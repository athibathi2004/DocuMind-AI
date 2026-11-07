from pathlib import Path
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
from PIL import Image
import numpy as np


class PDFRenderer:
    """Renders PDF documents to raster images per page and extracts vector layout."""

    def __init__(self, dpi: int = 200):
        self.dpi = dpi
        self.zoom = dpi / 72.0  # standard PDF resolution is 72 dpi

    def render_pages_to_images(
        self, pdf_path: Path, output_dir: Path
    ) -> List[Tuple[int, Path, int, int]]:
        """
        Renders each page of a PDF file to high-resolution PNG image on disk.
        Returns a list of (page_number, image_path, width, height).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(pdf_path)
        rendered_pages: List[Tuple[int, Path, int, int]] = []

        mat = fitz.Matrix(self.zoom, self.zoom)

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=mat, alpha=False)

            page_img_path = output_dir / f"page_{page_num}.png"
            pix.save(str(page_img_path))

            rendered_pages.append((page_num, page_img_path, pix.width, pix.height))

        doc.close()
        return rendered_pages

    def extract_embedded_text(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Extract vector text blocks already embedded in a digital PDF.
        Useful as high-accuracy ground truth when available.
        """
        doc = fitz.open(pdf_path)
        pages_data = []

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
            extracted_blocks = []

            for b in blocks:
                text = b[4].strip()
                if text:
                    extracted_blocks.append({
                        "bbox": [b[0], b[1], b[2], b[3]],
                        "text": text,
                        "block_num": b[5],
                    })

            pages_data.append({
                "page_number": page_num,
                "blocks": extracted_blocks,
                "full_text": page.get_text("text"),
            })

        doc.close()
        return pages_data


default_pdf_renderer = PDFRenderer()

