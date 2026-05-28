from __future__ import annotations


def chunk_text(text: str, chunk_size: int = 1100, overlap: int = 160) -> list[str]:
    """Split text into overlapping chunks while preserving paragraph boundaries."""

    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(cleaned) <= chunk_size:
        return [cleaned] if cleaned else []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        paragraph_break = cleaned.rfind("\n", start, end)
        if paragraph_break > start + chunk_size // 2:
            end = paragraph_break
        chunks.append(cleaned[start:end].strip())
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]
