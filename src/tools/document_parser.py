"""Document parser for loading and structuring source materials."""

import os
from pathlib import Path
from typing import Dict, Any


def load_source_document(file_path: str) -> Dict[str, Any]:
    """Reads and parses a source document (Markdown, TXT, or PDF) into structured content.

    Returns:
        Dict with 'file_name', 'content', 'word_count', and 'line_count'.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Source file not found at: {file_path}")

    ext = path.suffix.lower()

    if ext in [".md", ".txt", ".markdown"]:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    elif ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            content = "\n\n--- Page Break ---\n\n".join(pages)
        except ImportError:
            raise ImportError("To parse PDF documents, install pypdf: `pip install pypdf`")
    else:
        # Fallback to UTF-8 text read
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    lines = content.splitlines()
    words = content.split()

    return {
        "file_name": path.name,
        "file_path": str(path),
        "content": content,
        "line_count": len(lines),
        "word_count": len(words),
    }

