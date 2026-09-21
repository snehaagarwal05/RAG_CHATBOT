import io
from pypdf import PdfReader
from docx import Document


def extract_text(filename: str, raw: bytes) -> str:
    """Extract plain text from PDF, DOCX, or TXT bytes."""
    ext = filename.lower().rsplit(".", 1)[-1]

    if ext == "pdf":
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == "docx":
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)

    if ext == "txt":
        return raw.decode("utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type: .{ext}. Use PDF, DOCX, or TXT.")
