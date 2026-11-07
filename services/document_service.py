import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload, Session

from app.core.errors import DocumentNotFoundError, DuplicateDocumentError
from app.ingestion.storage import storage_manager
from app.models.document import (
    Document,
    DocumentPage,
    ProcessingJob,
    DocumentStatus,
    ProcessingStage,
    DocumentCategory,
)
from app.models.ocr import OCRResult, TextBlock
from app.models.extraction import ExtractedField
from app.models.validation import ValidationResult
from app.models.review import ReviewTask, ReviewStatus


class DocumentService:
    """Provides high-level document lifecycle, query, and analysis operations."""

    def ingest_document(
        self,
        session: Session,
        content: bytes,
        original_filename: str,
        mime_type: str,
    ) -> Document:
        """Saves physical file and creates Document record in DB, verifying duplicates."""
        doc_id, file_path, sha256_hash = storage_manager.save_file(content, original_filename)

        # Duplicate check
        existing = storage_manager.check_duplicate(session, sha256_hash)
        if existing:
            # Clean up the newly written file
            if file_path.exists():
                file_path.unlink()
            raise DuplicateDocumentError(
                f"Duplicate document detected (SHA-256 matches document {existing.id}).",
                existing_document_id=existing.id,
            )

        metadata = storage_manager.inspect_file(file_path, mime_type)

        doc = Document(
            id=doc_id,
            filename=file_path.name,
            original_filename=original_filename,
            file_path=str(file_path),
            mime_type=mime_type,
            file_size_bytes=len(content),
            sha256_hash=sha256_hash,
            page_count=metadata.get("page_count", 1),
            status=DocumentStatus.PENDING,
            current_stage=ProcessingStage.UPLOAD,
            metadata_json=metadata,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc

    def list_documents(
        self,
        session: Session,
        status: Optional[DocumentStatus] = None,
        category: Optional[DocumentCategory] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Document]]:
        """List documents with optional filtering and pagination."""
        stmt = select(Document)

        if status:
            stmt = stmt.where(Document.status == status)
        if category:
            stmt = stmt.where(Document.category == category)
        if search:
            stmt = stmt.where(Document.original_filename.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(count_stmt).scalar() or 0

        stmt = stmt.order_by(Document.created_at.desc()).limit(limit).offset(offset)
        result = session.execute(stmt)
        return total, list(result.scalars().all())

    def get_document(
        self, session: Session, document_id: str
    ) -> Document:
        """Fetch full document entity with all relationships."""
        stmt = (
            select(Document)
            .options(
                selectinload(Document.pages).selectinload(DocumentPage.text_blocks),
                selectinload(Document.ocr_results),
                selectinload(Document.extracted_fields),
                selectinload(Document.validation_results),
                selectinload(Document.processing_jobs),
                selectinload(Document.review_tasks).selectinload(ReviewTask.history),
            )
            .where(Document.id == document_id)
        )
        res = session.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")
        return doc

    def delete_document(
        self, session: Session, document_id: str
    ) -> bool:
        """Delete document record and associated disk files."""
        stmt = select(Document).where(Document.id == document_id)
        res = session.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")

        # Remove source file
        try:
            fpath = Path(doc.file_path)
            if fpath.exists():
                fpath.unlink()
        except Exception:
            pass

        session.delete(doc)
        session.commit()
        return True

    def get_analytics_overview(
        self, session: Session
    ) -> Dict[str, Any]:
        """Aggregate platform metrics for the overview dashboard."""
        # Total documents
        total_stmt = select(func.count(Document.id))
        total_docs = session.execute(total_stmt).scalar() or 0

        # Processed
        processed_stmt = select(func.count(Document.id)).where(
            Document.status.in_([DocumentStatus.COMPLETED, DocumentStatus.NEEDS_REVIEW])
        )
        processed_docs = session.execute(processed_stmt).scalar() or 0

        # Pending reviews
        reviews_stmt = select(func.count(ReviewTask.id)).where(
            ReviewTask.status == ReviewStatus.PENDING
        )
        pending_reviews = session.execute(reviews_stmt).scalar() or 0

        # Failed jobs
        failed_stmt = select(func.count(Document.id)).where(
            Document.status == DocumentStatus.FAILED
        )
        failed_jobs = session.execute(failed_stmt).scalar() or 0

        # Average confidence
        avg_conf_stmt = select(func.avg(Document.overall_confidence)).where(
            Document.overall_confidence.isnot(None)
        )
        avg_conf = session.execute(avg_conf_stmt).scalar() or 0.0

        # Group by status
        status_stmt = select(Document.status, func.count(Document.id)).group_by(Document.status)
        status_rows = session.execute(status_stmt).all()
        by_status = [{"status": str(r[0].value), "count": int(r[1])} for r in status_rows]

        # Group by category
        cat_stmt = select(Document.category, func.count(Document.id)).group_by(Document.category)
        cat_rows = session.execute(cat_stmt).all()
        by_cat = [{"category": str(r[0].value), "count": int(r[1])} for r in cat_rows]

        return {
            "total_documents": total_docs,
            "processed_documents": processed_docs,
            "pending_reviews": pending_reviews,
            "failed_jobs": failed_jobs,
            "average_confidence": round(float(avg_conf), 4),
            "documents_by_status": by_status,
            "documents_by_category": by_cat,
            "recent_activity_count_24h": total_docs,
        }


document_service = DocumentService()
