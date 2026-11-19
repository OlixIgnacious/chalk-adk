"""Document parser with security guardrails, malware scanning, and page-range budgeting."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.tools.guardrails import DocumentGuardrails, SecurityViolation


def parse_page_range(range_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parses a page range string like '1-20' or '15-30' into 1-based (start, end) tuples."""
    if not range_str:
        return None
    try:
        parts = range_str.strip().split("-")
        if len(parts) == 1:
            val = int(parts[0])
            return (val, val)
        return (int(parts[0]), int(parts[1]))
    except Exception:
        raise ValueError(f"Invalid page range format: '{range_str}'. Use format like '1-20' or '5-15'.")


def load_source_document(
    file_path: str,
    page_range: Optional[str] = None,
    allow_suspicious: bool = False,
) -> Dict[str, Any]:
    """Reads and parses source materials with security validation and token budgeting.

    Args:
        file_path: Path to target file
        page_range: Optional string like '1-20' to extract specific chapters from large PDFs
        allow_suspicious: If True, continues with a warning when dangerous PDF tags are detected

    Returns:
        Dict with parsed content, word counts, and security audit metadata.
    """
    # 1. Path & Size Validation
    path = DocumentGuardrails.validate_file_path(file_path)
    ext = path.suffix.lower()
    security_warnings = []

    # 2. PDF Parsing & Malware Scan
    if ext == ".pdf":
        # Scan for PDF exploit tags
        pdf_threats = DocumentGuardrails.scan_pdf_for_exploits(path)
        if pdf_threats:
            msg = f"Security Alert in '{path.name}':\n" + "\n".join(f" - {t}" for t in pdf_threats)
            if not allow_suspicious:
                raise SecurityViolation(
                    f"{msg}\n\nOperation halted to protect your system. "
                    "If you are certain this PDF is safe, re-run with --allow-suspicious."
                )
            security_warnings.extend(pdf_threats)

        try:
            import pypdf
        except ImportError:
            raise ImportError("To parse PDF documents, install pypdf: `pip install pypdf`")

        reader = pypdf.PdfReader(str(path))
        total_pages = len(reader.pages)

        # Apply Page Range or Budget Cap
        range_tuple = parse_page_range(page_range)
        if range_tuple:
            start_p, end_p = range_tuple
            start_idx = max(0, start_p - 1)
            end_idx = min(total_pages, end_p)
            selected_pages = list(range(start_idx, end_idx))
            print(f"📄 Extracting pages {start_p} to {end_p} (of {total_pages} total pages)...")
        else:
            if total_pages > DocumentGuardrails.MAX_DEFAULT_PAGES:
                print(
                    f"⚠️ Large Document Warning: PDF has {total_pages} pages. "
                    f"Processing the first {DocumentGuardrails.MAX_DEFAULT_PAGES} pages to protect Free Tier quotas. "
                    "Use `--page-range X-Y` to select specific chapters."
                )
                selected_pages = list(range(DocumentGuardrails.MAX_DEFAULT_PAGES))
            else:
                selected_pages = list(range(total_pages))

        extracted_chunks = []
        for i in selected_pages:
            try:
                page_text = reader.pages[i].extract_text() or ""
                extracted_chunks.append(f"--- Page {i + 1} ---\n{page_text}")
            except Exception as e:
                security_warnings.append(f"Failed to read page {i + 1}: {e}")

        content = "\n\n".join(extracted_chunks)

    elif ext in [".md", ".txt", ".markdown"]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    # 3. Prompt Injection Scan
    injections = DocumentGuardrails.scan_text_for_prompt_injection(content)
    if injections:
        security_warnings.extend(injections)
        print(f"🛡️ Guardrails: Neutralized {len(injections)} potential prompt injection pattern(s).")

    # Sanitize content enclosure
    sanitized_content = DocumentGuardrails.sanitize_untrusted_text(content)

    lines = content.splitlines()
    words = content.split()
    estimated_tokens = int(len(content) / 4)

    return {
        "file_name": path.name,
        "file_path": str(path),
        "content": sanitized_content,
        "raw_content": content,
        "line_count": len(lines),
        "word_count": len(words),
        "estimated_tokens": estimated_tokens,
        "security_warnings": security_warnings,
    }
