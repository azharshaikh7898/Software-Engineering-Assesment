import io
import os

from pypdf import PdfReader


class IngestError(Exception):
    """A user-facing reason why a document cannot be processed."""


def _clean(text: str) -> str:
    return text.replace("\x00", "")  # Postgres text columns reject NUL bytes


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise IngestError("PDF is password-protected")
            pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
        except IngestError:
            raise
        except Exception as exc:
            raise IngestError("Could not read this PDF (corrupt or unsupported)") from exc
    elif ext in (".txt", ".md"):
        pages = [(None, data.decode("utf-8", errors="replace"))]
    else:
        raise IngestError("Unsupported file type")

    pages = [(n, _clean(t)) for n, t in pages if t.strip()]
    if not pages:
        raise IngestError("No extractable text (scanned PDF? OCR is not supported)")
    return pages
