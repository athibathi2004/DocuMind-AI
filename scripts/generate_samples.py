import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF


def create_passport_image(output_path: Path):
    """Generate a synthetic passport document image with realistic layout and valid MRZ."""
    width, height = 850, 600
    img = Image.new("RGB", (width, height), color=(248, 246, 240))
    draw = ImageDraw.Draw(img)

    # Decorative border
    draw.rectangle([15, 15, width - 15, height - 15], outline=(180, 160, 120), width=3)
    draw.rectangle([25, 25, width - 25, height - 25], outline=(210, 195, 160), width=1)

    # Header
    draw.text((320, 45), "PASSPORT / PASSEPORT", fill=(20, 30, 80))
    draw.text((280, 75), "UNITED STATES OF AMERICA", fill=(20, 30, 80))

    # Photo placeholder
    draw.rectangle([50, 130, 230, 370], fill=(225, 230, 240), outline=(120, 130, 150), width=2)
    draw.text((95, 240), "[ PHOTO ]", fill=(100, 110, 130))

    # Visual Inspection Zone details
    details = [
        ("Type / Type", "P", 270, 130),
        ("Country Code", "USA", 430, 130),
        ("Passport No.", "A12345678", 580, 130),
        ("Surname / Nom", "HENDRICKS", 270, 175),
        ("Given Names / Prénoms", "ELEANOR JANE", 270, 220),
        ("Nationality / Nationalité", "UNITED STATES OF AMERICA", 270, 265),
        ("Date of Birth / Date de naissance", "14 APR 1988", 270, 310),
        ("Sex / Sexe", "F", 580, 310),
        ("Place of Birth / Lieu de naissance", "CALIFORNIA, U.S.A.", 270, 355),
        ("Date of Issue / Date de délivrance", "12 JUN 2021", 270, 400),
        ("Date of Expiration / Date d'expiration", "11 JUN 2031", 520, 400),
        ("Authority / Autorité", "UNITED STATES DEPARTMENT OF STATE", 270, 445),
    ]

    for label, val, x, y in details:
        draw.text((x, y), label, fill=(110, 110, 120))
        draw.text((x, y + 16), val, fill=(10, 15, 30))

    # Machine Readable Zone (MRZ) - 2 lines of 44 characters
    draw.rectangle([40, 490, width - 40, height - 30], fill=(240, 238, 230), outline=(200, 190, 170))
    mrz1 = "P<USAHENDRICKS<<ELEANOR<JANE<<<<<<<<<<<<<<<<"
    mrz2 = "A123456787USA8804144F3106114<<<<<<<<<<<<<<06"

    draw.text((60, 505), mrz1, fill=(0, 0, 0))
    draw.text((60, 535), mrz2, fill=(0, 0, 0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    print(f"Generated synthetic passport image: {output_path}")


def create_invoice_pdf(output_path: Path):
    """Generate a clean synthetic invoice PDF using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Top brand banner
    page.draw_rect(fitz.Rect(40, 40, 555, 100), color=(0.1, 0.2, 0.4), fill=(0.1, 0.2, 0.4))
    page.insert_text(fitz.Point(60, 75), "Acme Industrial Technologies Ltd.", fontsize=18, color=(1, 1, 1))
    page.insert_text(fitz.Point(460, 75), "INVOICE", fontsize=20, color=(1, 1, 1))

    # Metadata
    page.insert_text(fitz.Point(40, 130), "Invoice Number: INV-2026-0842", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(40, 150), "Invoice Date: 2026-03-15", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(40, 170), "Due Date: 2026-04-15", fontsize=11, color=(0.1, 0.1, 0.1))

    page.insert_text(fitz.Point(340, 130), "Billed To: Global Systems Corp", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(340, 150), "Customer Address: 450 Innovation Parkway", fontsize=10, color=(0.3, 0.3, 0.3))
    page.insert_text(fitz.Point(340, 170), "Tax ID: US-94810294", fontsize=10, color=(0.3, 0.3, 0.3))

    # Table Header
    page.draw_rect(fitz.Rect(40, 220, 555, 245), fill=(0.9, 0.92, 0.95))
    page.insert_text(fitz.Point(50, 237), "Description | Qty | Unit Price | Total", fontsize=10, color=(0.1, 0.1, 0.1))

    # Line items
    page.insert_text(fitz.Point(50, 270), "Cloud Enterprise Subscription | 1 | $1,250.00 | $1,250.00", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, 300), "Managed Security Operations | 1 | $750.00 | $750.00", fontsize=10, color=(0.2, 0.2, 0.2))
    page.draw_line(fitz.Point(40, 330), fitz.Point(555, 330), color=(0.8, 0.8, 0.8), width=1)

    # Totals block
    page.insert_text(fitz.Point(350, 360), "Subtotal: $2,000.00", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(350, 385), "Tax: $180.00", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(350, 415), "Total Amount: $2,180.00", fontsize=13, color=(0.1, 0.2, 0.5))
    page.insert_text(fitz.Point(350, 440), "Currency: USD", fontsize=10, color=(0.4, 0.4, 0.4))

    # Footer
    page.insert_text(fitz.Point(40, 520), "Payment Terms: Net 30 days. Thank you for your business.", fontsize=10, color=(0.4, 0.4, 0.4))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Generated synthetic invoice PDF: {output_path}")


def create_invoice_image(pdf_path: Path, output_path: Path):
    """Render the invoice PDF to PNG."""
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    pix.save(str(output_path))
    doc.close()
    print(f"Generated synthetic invoice PNG: {output_path}")


def create_contract_pdf(output_path: Path):
    """Generate a synthetic contract PDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text(fitz.Point(160, 80), "MASTER SERVICES AGREEMENT", fontsize=16, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(50, 130), "This Agreement is entered into on 2026-01-10.", fontsize=11, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, 160), "Between: Apex Technologies Inc.", fontsize=11, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, 185), "And: Horizon Logistics LLC", fontsize=11, color=(0.2, 0.2, 0.2))

    page.insert_text(fitz.Point(50, 230), "1. Scope of Work and Deliverables", fontsize=13, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(50, 260), "The Consultant agrees to provide document processing architectures.", fontsize=10, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(50, 310), "Effective Date: 2026-01-15", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(50, 380), "Signatures: Authorized Representative", fontsize=10, color=(0.3, 0.3, 0.3))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Generated synthetic contract PDF: {output_path}")


def create_general_txt(output_path: Path):
    content = (
        "EXECUTIVE MEMORANDUM\n"
        "Organization: Department of Architecture\n"
        "Date: 2026-02-20\n"
        "Subject: Modern Document Intelligence Pipeline\n"
        "Key Information: Migration to layout-aware extraction completed successfully.\n"
        "All validation checkpoints and human-in-the-loop review queues are operational.\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated synthetic general document TXT: {output_path}")


def generate_all():
    base_dir = Path(__file__).resolve().parent.parent / "sample-data"
    base_dir.mkdir(parents=True, exist_ok=True)

    create_passport_image(base_dir / "sample_passport.png")
    invoice_pdf = base_dir / "sample_invoice.pdf"
    create_invoice_pdf(invoice_pdf)
    create_invoice_image(invoice_pdf, base_dir / "sample_invoice.png")
    create_contract_pdf(base_dir / "sample_contract.pdf")
    create_general_txt(base_dir / "sample_general.txt")


if __name__ == "__main__":
    generate_all()

