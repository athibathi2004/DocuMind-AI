import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload, Session

from app.config import settings
from app.core.logging import logger
from app.core.errors import DocumentNotFoundError, ProcessingError
from app.models.document import (
    Document,
    DocumentPage,
    ProcessingJob,
    DocumentStatus,
    ProcessingStage,
    DocumentCategory,
)
from app.models.ocr import OCRResult, TextBlock, BlockType
from app.models.extraction import ExtractedField, ValidationStatus
from app.models.validation import ValidationResult, ValidationRuleStatus
from app.models.review import ReviewTask, ReviewStatus
from app.preprocessing import default_image_processor, default_pdf_renderer
from app.ocr import get_ocr_engine, OCRPageData
from app.layout import default_layout_analyzer
from app.classification import default_classifier
from app.extraction import default_extraction_orchestrator
from app.confidence import default_confidence_assessor
from app.validation import default_validation_engine


class ProcessingPipelineOrchestrator:
    """
    End-to-End Orchestrator executing the complete document intelligence workflow:
    Ingestion -> Preprocessing -> OCR -> Layout -> Classification ->
    Extraction -> Confidence Assessment -> Validation -> HITL Review Routing -> Persistence.
    """

    def process_document(
        self,
        session: Session,
        document_id: str,
        ocr_provider: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> Document:
        """Execute the end-to-end processing pipeline for a given document."""
        threshold = confidence_threshold or settings.DEFAULT_CONFIDENCE_THRESHOLD

        # Fetch document
        stmt = (
            select(Document)
            .options(
                selectinload(Document.pages),
                selectinload(Document.ocr_results),
                selectinload(Document.extracted_fields),
                selectinload(Document.validation_results),
                selectinload(Document.review_tasks),
            )
            .where(Document.id == document_id)
        )
        res = session.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")

        # Update document state to PROCESSING
        doc.status = DocumentStatus.PROCESSING
        doc.current_stage = ProcessingStage.PREPROCESSING
        session.commit()

        job_start_time = time.time()
        job = ProcessingJob(
            document_id=doc.id,
            stage=ProcessingStage.PREPROCESSING,
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
        session.commit()

        try:
            file_path = Path(doc.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Source file not found at path: {file_path}")

            # -------------------------------------------------------------
            # STAGE 1: Page Rendering & Image Preprocessing
            # -------------------------------------------------------------
            logger.info(f"[{doc.id}] Stage 1: Preprocessing & Rendering")
            doc.current_stage = ProcessingStage.PREPROCESSING
            job.stage = ProcessingStage.PREPROCESSING

            rendered_pages: List[Dict[str, Any]] = []
            ext = file_path.suffix.lower()
            doc_output_dir = settings.PROCESSED_DIR / doc.id
            doc_output_dir.mkdir(parents=True, exist_ok=True)

            if ext == ".pdf":
                pages_meta = default_pdf_renderer.render_pages_to_images(
                    file_path, doc_output_dir
                )
                for page_num, img_path, w, h in pages_meta:
                    preprocessed_arr, prep_diag = default_image_processor.process(img_path)
                    prep_img_path = doc_output_dir / f"preprocessed_page_{page_num}.png"
                    default_image_processor.save_image(preprocessed_arr, prep_img_path)
                    rendered_pages.append({
                        "page_number": page_num,
                        "raw_image_path": str(img_path),
                        "preprocessed_path": str(prep_img_path),
                        "width": w,
                        "height": h,
                    })
            elif ext in [".png", ".jpg", ".jpeg"]:
                preprocessed_arr, prep_diag = default_image_processor.process(file_path)
                prep_img_path = doc_output_dir / f"preprocessed_page_1.png"
                default_image_processor.save_image(preprocessed_arr, prep_img_path)
                h, w = preprocessed_arr.shape[:2]
                rendered_pages.append({
                    "page_number": 1,
                    "raw_image_path": str(file_path),
                    "preprocessed_path": str(prep_img_path),
                    "width": w,
                    "height": h,
                })
            else:
                rendered_pages.append({
                    "page_number": 1,
                    "raw_image_path": str(file_path),
                    "preprocessed_path": str(file_path),
                    "width": 800,
                    "height": 1000,
                })

            doc.page_count = len(rendered_pages)

            # Persist or update DocumentPage models
            created_pages: List[DocumentPage] = []
            for p_info in rendered_pages:
                page_obj = DocumentPage(
                    document_id=doc.id,
                    page_number=p_info["page_number"],
                    image_path=p_info["raw_image_path"],
                    preprocessed_path=p_info["preprocessed_path"],
                    width=p_info["width"],
                    height=p_info["height"],
                )
                session.add(page_obj)
                created_pages.append(page_obj)

            session.flush()

            # -------------------------------------------------------------
            # STAGE 2: OCR Engine Execution
            # -------------------------------------------------------------
            logger.info(f"[{doc.id}] Stage 2: OCR Engine")
            doc.current_stage = ProcessingStage.OCR
            job.stage = ProcessingStage.OCR

            ocr_engine = get_ocr_engine(ocr_provider)
            ocr_pages: List[OCRPageData] = []

            for p_obj in created_pages:
                target_img = p_obj.preprocessed_path or p_obj.image_path
                ocr_page = ocr_engine.extract_page(
                    target_img,
                    page_number=p_obj.page_number,
                    doc_name_hint=doc.original_filename,
                )
                ocr_pages.append(ocr_page)

                # Persist text blocks
                for blk in ocr_page.blocks:
                    b_type = BlockType.LINE
                    if blk.block_type in BlockType.__members__:
                        b_type = BlockType[blk.block_type]

                    tb_record = TextBlock(
                        page_id=p_obj.id,
                        page_number=blk.page_number,
                        text=blk.text,
                        confidence=blk.confidence,
                        block_type=b_type,
                        reading_order=blk.reading_order,
                        bbox_x_min=blk.bbox.x_min,
                        bbox_y_min=blk.bbox.y_min,
                        bbox_x_max=blk.bbox.x_max,
                        bbox_y_max=blk.bbox.y_max,
                        polygon=blk.bbox.polygon,
                    )
                    session.add(tb_record)

            # Persist OCRResult aggregate
            full_text = "\n\n".join(p.raw_text for p in ocr_pages)
            total_blocks_count = sum(len(p.blocks) for p in ocr_pages)
            avg_ocr_conf = (
                sum(p.average_confidence for p in ocr_pages) / len(ocr_pages)
                if ocr_pages else 0.0
            )

            ocr_result_record = OCRResult(
                document_id=doc.id,
                provider=ocr_engine.name,
                page_count=len(ocr_pages),
                total_blocks=total_blocks_count,
                raw_text=full_text,
                average_confidence=round(avg_ocr_conf, 4),
                execution_time_ms=sum(p.execution_time_ms for p in ocr_pages),
                diagnostics={"pages": [p.diagnostics for p in ocr_pages]},
            )
            session.add(ocr_result_record)
            session.flush()

            # -------------------------------------------------------------
            # STAGE 3: Layout Intelligence
            # -------------------------------------------------------------
            logger.info(f"[{doc.id}] Stage 3: Layout Intelligence")
            doc.current_stage = ProcessingStage.LAYOUT
            job.stage = ProcessingStage.LAYOUT

            all_ocr_blocks = [b for p in ocr_pages for b in p.blocks]
            layout_structure = default_layout_analyzer.analyze(all_ocr_blocks)

            # -------------------------------------------------------------
            # STAGE 4: Document Classification
            # -------------------------------------------------------------
            logger.info(f"[{doc.id}] Stage 4: Classification")
            doc.current_stage = ProcessingStage.CLASSIFICATION
            job.stage = ProcessingStage.CLASSIFICATION

            category, cat_conf, cat_expl, cat_diag = default_classifier.classify(ocr_pages)
            doc.category = category
            doc.classification_confidence = cat_conf
            doc.classification_explanation = cat_expl

            # -------------------------------------------------------------
            # STAGE 5: Structured Field Extraction
            # -------------------------------------------------------------
            logger.info(f"[{doc.id}] Stage 5: Structured Field Extraction ({category.value})")
            doc.current_stage = ProcessingStage.EXTRACTION
            job.stage = ProcessingStage.EXTRACTION

            raw_fields = default_extraction_orchestrator.extract_fields(
                category, ocr_pages, layout_structure
            )

            # -------------------------------------------------------------
            # STAGE 6: Validation Engine
            # -------------------------------------------------------------
            logger.info(f"[{doc.id}] Stage 6: Validation Engine")
            doc.current_stage = ProcessingStage.VALIDATION
            job.stage = ProcessingStage.VALIDATION

            val_results, field_statuses, normalized_vals = default_validation_engine.validate_document_fields(
                category, raw_fields
            )

            for vr in val_results:
                v_record = ValidationResult(
                    document_id=doc.id,
                    rule_name=vr["rule_name"],
                    rule_type=vr["rule_type"],
                    field_name=vr.get("field_name"),
                    status=vr["status"],
                    message=vr["message"],
                    details=vr.get("details", {}),
                )
                session.add(v_record)

            # -------------------------------------------------------------
            # STAGE 7: Confidence Assessment
            # -------------------------------------------------------------
            logger.info(f"[{doc.id}] Stage 7: Confidence Assessment")
            doc.current_stage = ProcessingStage.CONFIDENCE
            job.stage = ProcessingStage.CONFIDENCE

            assessor = default_confidence_assessor
            assessor.threshold = threshold

            field_confidences: List[float] = []
            flagged_fields_count = 0

            for raw_f in raw_fields:
                f_name = raw_f.field_name
                val_status = field_statuses.get(f_name, ValidationStatus.VALID)
                comp_conf, val_conf, rev_req = assessor.assess_field(raw_f, val_status)

                field_confidences.append(comp_conf)
                if rev_req:
                    flagged_fields_count += 1

                norm_val = normalized_vals.get(f_name, raw_f.field_value)

                f_record = ExtractedField(
                    document_id=doc.id,
                    field_name=raw_f.field_name,
                    field_value=raw_f.field_value,
                    normalized_value=norm_val,
                    field_type=raw_f.field_type,
                    confidence=comp_conf,
                    ocr_confidence=raw_f.ocr_confidence,
                    extraction_confidence=raw_f.extraction_confidence,
                    validation_confidence=val_conf,
                    validation_status=val_status,
                    review_required=rev_req,
                    source_page=raw_f.source_page,
                    source_text=raw_f.source_text,
                    bounding_box=raw_f.bounding_box,
                )
                session.add(f_record)

            overall_confidence = assessor.compute_document_overall_confidence(field_confidences)
            doc.overall_confidence = overall_confidence

            # -------------------------------------------------------------
            # STAGE 8: Human-in-the-Loop Routing
            # -------------------------------------------------------------
            any_val_failure = any(
                vr["status"] == ValidationRuleStatus.FAIL for vr in val_results
            )

            needs_review = (flagged_fields_count > 0) or any_val_failure

            if needs_review:
                logger.info(f"[{doc.id}] Document requires human review (Flagged fields: {flagged_fields_count})")
                doc.status = DocumentStatus.NEEDS_REVIEW
                doc.current_stage = ProcessingStage.REVIEW

                review_task = ReviewTask(
                    document_id=doc.id,
                    status=ReviewStatus.PENDING,
                    flagged_fields_count=flagged_fields_count,
                    reviewer_notes=f"Flagged {flagged_fields_count} field(s) below confidence threshold {threshold:.2f} or failing validation.",
                )
                session.add(review_task)
            else:
                doc.status = DocumentStatus.COMPLETED
                doc.current_stage = ProcessingStage.COMPLETED

            # Complete Processing Job
            job.status = "SUCCESS"
            job.completed_at = datetime.now(timezone.utc)
            job.duration_ms = int((time.time() - job_start_time) * 1000)
            job.diagnostics = {
                "overall_confidence": overall_confidence,
                "flagged_fields": flagged_fields_count,
                "needs_review": needs_review,
                "pages_processed": len(ocr_pages),
            }

            session.commit()
            session.refresh(doc)
            return doc

        except Exception as e:
            logger.error(f"[{doc.id}] Pipeline failed at stage '{doc.current_stage}': {e}", exc_info=True)
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)

            job.status = "FAILED"
            job.completed_at = datetime.now(timezone.utc)
            job.duration_ms = int((time.time() - job_start_time) * 1000)
            job.error = str(e)

            session.commit()
            raise ProcessingError(doc.current_stage.value, str(e))


pipeline_orchestrator = ProcessingPipelineOrchestrator()
