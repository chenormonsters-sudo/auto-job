import zipfile
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader


class ResumeParseError(RuntimeError):
    pass


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        return _extract_docx_text(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ResumeParseError(f"不支持的简历格式: {suffix}")


def _extract_docx_text(path: Path) -> str:
    """Extract body text including text boxes, which python-docx paragraphs miss."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    lines = []
    seen = set()
    for paragraph in root.findall(".//w:p", ns):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", ns)]
        text = "".join(texts)
        if text and text not in seen:
            seen.add(text)
            lines.append(text)
    return "\n".join(lines)
