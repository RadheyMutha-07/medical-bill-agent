"""
extractor.py - PDF and image text extraction
Supports: PDF (via PyMuPDF), images (via Pillow + pytesseract), plain text files
"""

import os


def extract_text_from_pdf(path: str) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF not installed. Run: pip install PyMuPDF")

    doc = fitz.open(path)
    pages_text = []
    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        if text.strip():
            pages_text.append(f"[Page {page_num}]\n{text}")
        else:
            # Page has no selectable text - try OCR via image rendering
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            ocr_text = _ocr_from_bytes(img_bytes)
            if ocr_text.strip():
                pages_text.append(f"[Page {page_num} - OCR]\n{ocr_text}")
    doc.close()
    return "\n\n".join(pages_text)


def extract_text_from_image(path: str) -> str:
    """Extract text from an image file using pytesseract OCR."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        raise ImportError("Pillow or pytesseract not installed. Run: pip install Pillow pytesseract")

    img = Image.open(path)
    # Convert to RGB if needed
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    text = pytesseract.image_to_string(img, config="--psm 6")
    return text


def _ocr_from_bytes(img_bytes: bytes) -> str:
    """Run OCR on image bytes (used for scanned PDF pages)."""
    try:
        from PIL import Image
        import pytesseract
        import io
    except ImportError:
        return ""

    img = Image.open(io.BytesIO(img_bytes))
    return pytesseract.image_to_string(img, config="--psm 6")


def extract_text(path: str) -> str:
    """
    Detect file type and extract text accordingly.
    Supports: .pdf, .png, .jpg, .jpeg, .tiff, .bmp, .gif, .txt
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"):
        return extract_text_from_image(path)
    elif ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            "Supported: .pdf, .png, .jpg, .jpeg, .tiff, .bmp, .gif, .txt"
        )
