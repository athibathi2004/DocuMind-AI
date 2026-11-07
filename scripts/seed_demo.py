import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal, init_db
from app.services.document_service import document_service
from app.pipeline.orchestrator import pipeline_orchestrator
from app.core.errors import DuplicateDocumentError


def seed():
    print("Initializing DocuMind AI database...")
    init_db()

    sample_dir = Path(__file__).resolve().parent.parent / "sample-data"
    sample_files = [
        sample_dir / "sample_invoice.pdf",
        sample_dir / "sample_passport.png",
        sample_dir / "sample_contract.pdf",
        sample_dir / "sample_general.txt",
    ]

    with SessionLocal() as session:
        for fpath in sample_files:
            if not fpath.exists():
                print(f"Skipping missing sample file: {fpath}")
                continue

            print(f"\nProcessing sample document: {fpath.name}")
            with open(fpath, "rb") as f:
                content = f.read()

            try:
                doc = document_service.ingest_document(
                    session=session,
                    content=content,
                    original_filename=fpath.name,
                    mime_type="application/pdf" if fpath.suffix == ".pdf" else "image/png",
                )
                print(f"  Ingested Document: {doc.id}")

                # Process document
                processed = pipeline_orchestrator.process_document(
                    session=session,
                    document_id=doc.id,
                    ocr_provider="mock",
                )
                print(f"  Processed status: {processed.status.value}, Category: {processed.category.value}")
            except DuplicateDocumentError:
                print(f"  Document '{fpath.name}' already seeded.")
            except Exception as e:
                print(f"  Error processing {fpath.name}: {e}")

    print("\nDemo database seeded successfully!")


if __name__ == "__main__":
    seed()
