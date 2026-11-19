"""Document parser with security guardrails, malware scanning, page budgeting, and EPUB support."""

import re
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.tools.guardrails import DocumentGuardrails, SecurityViolation


class HTMLTextExtractor(HTMLParser):
    """Fast, safe in-memory HTML tag stripper for EPUB chapters."""
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self) -> str:
        return " ".join("".join(self.text_parts).split())


def extract_epub_content(epub_path: Path, target_chapter: Optional[int] = None) -> str:
    """Extracts sequential chapter text from an unencrypted EPUB file."""
    with zipfile.ZipFile(str(epub_path), "r") as z:
        # Locate .opf package file
        try:
            container_xml = z.read("META-INF/container.xml")
            container_root = ET.fromstring(container_xml)
            rootfile_el = container_root.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
            if rootfile_el is None:
                raise ValueError("Invalid EPUB: Missing rootfile in container.xml")
            opf_path = rootfile_el.attrib["full-path"]
        except Exception as e:
            raise ValueError(f"Could not read EPUB container structure: {e}")

        opf_dir = str(Path(opf_path).parent)
        opf_data = z.read(opf_path)
        opf_root = ET.fromstring(opf_data)

        # Build manifest map (id -> href)
        manifest = {}
        for item in opf_root.findall(".//{*}item"):
            manifest[item.attrib.get("id")] = item.attrib.get("href")

        # Extract spine order
        spine = [
            item.attrib.get("idref")
            for item in opf_root.findall(".//{*}itemref")
            if item.attrib.get("idref")
        ]

        total_chapters = len(spine)
        if target_chapter is not None:
            if 1 <= target_chapter <= total_chapters:
                spine = [spine[target_chapter - 1]]
                print(f"📖 Extracting Chapter {target_chapter} of {total_chapters} from EPUB...")
            else:
                raise ValueError(f"Chapter {target_chapter} out of range (Book has {total_chapters} chapters).")
        else:
            print(f"📖 Reading all {total_chapters} chapters from EPUB...")

        extracted_sections = []
        for idx, item_id in enumerate(spine):
            href = manifest.get(item_id)
            if not href:
                continue

            full_href = f"{opf_dir}/{href}" if opf_dir and opf_dir != "." else href
            # Normalize path inside zip
            full_href = full_href.replace("\\", "/")

            try:
                raw_html = z.read(full_href).decode("utf-8", errors="ignore")
                extractor = HTMLTextExtractor()
                extractor.feed(raw_html)
                clean_text = extractor.get_text()
                if len(clean_text) > 40:  # Skip trivial copyright / blank pages
                    chap_num = target_chapter if target_chapter is not None else (idx + 1)
                    extracted_sections.append(f"=== CHAPTER {chap_num} ===\n{clean_text}")
            except KeyError:
                continue

        return "\n\n".join(extracted_sections)


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
    chapter: Optional[int] = None,
    allow_suspicious: bool = False,
) -> Dict[str, Any]:
    """Reads and parses source materials (MD, TXT, PDF, EPUB) with guardrails and token budgeting.

    Args:
        file_path: Path to target file
        page_range: Optional string like '1-20' for PDFs
        chapter: Optional chapter number for EPUB books (e.g. 4)
        allow_suspicious: If True, continues with a warning when dangerous PDF tags are detected

    Returns:
        Dict with parsed content, word counts, and security audit metadata.
    """
    # 1. Path & Size Validation
    path = DocumentGuardrails.validate_file_path(file_path)
    ext = path.suffix.lower()
    security_warnings = []

    # 2. EPUB Books
    if ext == ".epub":
        content = extract_epub_content(path, target_chapter=chapter)

    # 3. PDF Documents
    elif ext == ".pdf":
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

    # 4. Markdown & Plain Text
    elif ext in [".md", ".txt", ".markdown"]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    # 5. Prompt Injection Scan
    injections = DocumentGuardrails.scan_text_for_prompt_injection(content)
    if injections:
        security_warnings.extend(injections)
        print(f"🛡️ Guardrails: Neutralized {len(injections)} potential prompt injection pattern(s).")

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
