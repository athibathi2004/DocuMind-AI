import sys
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal, init_db
from app.services.document_service import document_service
from app.pipeline.orchestrator import pipeline_orchestrator


def run_cli(file_path_str: str, ocr_provider: str = "mock"):
    file_path = Path(file_path_str)
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    print("=" * 70)
    print("DOCUMIND AI — Intelligent Document Processing CLI")
    print("=" * 70)
    print(f"Target File: {file_path.name}")
    print(f"OCR Provider: {ocr_provider}")

    init_db()

    with open(file_path, "rb") as f:
        content = f.read()

    with SessionLocal() as session:
        # 1. Ingest
        print("\n[Stage: Ingestion] Uploading and calculating SHA-256...")
        doc = document_service.ingest_document(
            session=session,
            content=content,
            original_filename=file_path.name,
            mime_type="application/octet-stream",
        )
        print(f"  -> Document ID: {doc.id}")
        print(f"  -> SHA-256 Hash: {doc.sha256_hash}")

        # 2. Process
        print("\n[Stage: Pipeline] Executing end-to-end extraction pipeline...")
        processed_doc = pipeline_orchestrator.process_document(
            session=session,
            document_id=doc.id,
            ocr_provider=ocr_provider,
        )

        # Refresh
        detail = document_service.get_document(session, doc.id)

        print("\n" + "=" * 70)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Status:             {detail.status.value}")
        print(f"Category:           {detail.category.value} (Confidence: {detail.classification_confidence or 0:.2f})")
        print(f"Explanation:        {detail.classification_explanation}")
        print(f"Overall Confidence: {detail.overall_confidence or 0:.2f}")
        print(f"Pages:              {detail.page_count}")

        print("\n--- EXTRACTED FIELDS ---")
        print(f"{'Field Name':<20} | {'Value':<30} | {'Conf':<6} | {'Status':<10} | {'Review'}")
        print("-" * 80)
        for f in detail.extracted_fields:
            val_str = str(f.field_value or "None")
            if len(val_str) > 28:
                val_str = val_str[:25] + "..."
            rev = "YES" if f.review_required else "No"
            print(f"{f.field_name:<20} | {val_str:<30} | {f.confidence:<6.2f} | {f.validation_status.value:<10} | {rev}")

        print("\n--- VALIDATION RESULTS ---")
        for v in detail.validation_results:
            icon = "[PASS]" if v.status.value == "PASS" else "[FAIL]" if v.status.value == "FAIL" else "[WARN]"
            print(f"  {icon} {v.rule_name}: {v.message}")

        if detail.review_tasks:
            print(f"\n[!] Human-in-the-Loop Review Task Created: ID={detail.review_tasks[0].id}")
            print(f"    Flagged Fields: {detail.review_tasks[0].flagged_fields_count}")

        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="DocuMind AI Document Pipeline CLI")
    parser.add_argument("file", help="Path to document file to process")
    parser.add_argument("--ocr", default="mock", choices=["mock", "paddle", "auto"], help="OCR provider")
    args = parser.parse_args()

    run_cli(args.file, args.ocr)


if __name__ == "__main__":
    main()
