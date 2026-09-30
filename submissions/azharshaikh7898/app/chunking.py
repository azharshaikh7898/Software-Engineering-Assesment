import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    page: int | None
    text: str


def _split_long(paragraph: str, size: int) -> list[str]:
    """Split an oversized paragraph on sentence boundaries; hard-split what is still too long."""
    out: list[str] = []
    cur = ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        while len(sentence) > size:
            if cur:
                out.append(cur)
                cur = ""
            out.append(sentence[:size])
            sentence = sentence[size:]
        if cur and len(cur) + 1 + len(sentence) > size:
            out.append(cur)
            cur = sentence
        else:
            cur = f"{cur} {sentence}" if cur else sentence
    if cur:
        out.append(cur)
    return out


def _tail(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    tail = text[-overlap:]
    if " " in tail:  # start on a word boundary
        tail = tail[tail.index(" ") + 1:]
    return tail


def chunk_pages(pages: list[tuple[int | None, str]], size: int = 800, overlap: int = 120) -> list[Chunk]:
    """Paragraph-aware chunks of about `size` chars with `overlap` chars carried over.

    Chunks never span pages, so a citation's page number is exact.
    """
    chunks: list[Chunk] = []
    for page, text in pages:
        pieces: list[str] = []
        for raw in re.split(r"\n\s*\n", text):
            para = re.sub(r"[ \t]+", " ", raw).strip()
            if not para:
                continue
            pieces.extend(_split_long(para, size) if len(para) > size else [para])

        cur = ""
        for piece in pieces:
            if cur and len(cur) + 2 + len(piece) > size:
                chunks.append(Chunk(page, cur))
                tail = _tail(cur, overlap)
                cur = f"{tail}\n\n{piece}" if tail else piece
            else:
                cur = f"{cur}\n\n{piece}" if cur else piece
        if cur.strip():
            chunks.append(Chunk(page, cur))
    return chunks
