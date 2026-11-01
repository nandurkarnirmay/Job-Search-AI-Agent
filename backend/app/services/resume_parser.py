"""Resume upload: validate, extract text from PDF/DOCX, redact contact details, detect sections and skills.
The original file is never stored: only the redacted text and the parsed fields."""
import io
import re
import zipfile

from app.domain import ParsedResume
from app.errors import AppError
from app.services.skills import extract_skills

MAX_BYTES = 2 * 1024 * 1024
MAX_PAGES = 6
MAX_DOCX_UNCOMPRESSED = 20 * 1024 * 1024  # zip-bomb guard
MAX_TEXT_CHARS = 30_000

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s\-]?)?(?:0)?[6-9]\d{4}[\s\-]?\d{5}(?!\d)|(?<!\d)\+\d{1,3}[\s\-]?\d{6,12}(?!\d)")

SECTIONS = {
    "summary": r"summary|profile|objective|about me|career objective|professional summary",
    "experience": r"experience|work experience|professional experience|employment|internships?|work history",
    "education": r"education|academic(?:s| background| qualifications?)?|qualifications?",
    "skills": r"skills|technical skills|key skills|core competencies|technologies|tech stack|skill set",
    "projects": r"projects?|academic projects|key projects|personal projects",
    "certifications": r"certifications?|courses|licen[cs]es",
    "achievements": r"achievements|awards|honou?rs|accomplishments",
    "responsibilities": r"positions? of responsibility|leadership|extra[- ]?curricular(?: activities)?|activities",
}
_HEADING = {k: re.compile(rf"^\s*(?:{v})\s*:?\s*$", re.I) for k, v in SECTIONS.items()}


class ResumeError(AppError):
    status_code = 400
    code = "invalid_resume"


def _pdf_text(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ResumeError("This PDF is password-protected. Upload an unprotected copy.")
        pages = len(reader.pages)
        if pages > MAX_PAGES:
            raise ResumeError(f"Resume has {pages} pages; the limit is {MAX_PAGES}.")
        return "\n".join((p.extract_text() or "") for p in reader.pages), pages
    except PdfReadError as e:
        raise ResumeError("Couldn't read this PDF. Re-export it from Word or Google Docs and try again.") from e


def _docx_text(data: bytes) -> tuple[str, int]:
    from docx import Document

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_DOCX_UNCOMPRESSED:
                raise ResumeError("This DOCX file is too large once unpacked.")
        doc = Document(io.BytesIO(data))
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise ResumeError("Couldn't read this DOCX file. Save it again from Word and retry.") from e
    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:  # many resume templates put whole sections in tables
        for row in table.rows:
            seen = []
            for cell in row.cells:
                if cell.text not in seen:  # merged cells repeat their text
                    seen.append(cell.text)
            lines.extend(seen)
    return "\n".join(lines), 0


def extract_text(filename: str, data: bytes) -> tuple[str, str, int]:
    """(text, kind, pages). Validates by content (magic bytes), not by the file extension."""
    if not data:
        raise ResumeError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise ResumeError("File is larger than 2 MB.")
    if data[:5] == b"%PDF-":
        text, pages = _pdf_text(data)
        return text[:MAX_TEXT_CHARS], "pdf", pages
    if data[:4] == b"PK\x03\x04" and filename.lower().endswith(".docx"):
        text, pages = _docx_text(data)
        return text[:MAX_TEXT_CHARS], "docx", pages
    raise ResumeError("Upload a PDF or DOCX file.")


def redact(text: str) -> tuple[str, bool]:
    """Remove emails and phone numbers. Returns (redacted text, whether any contact detail was found)."""
    found = bool(EMAIL.search(text) or PHONE.search(text))
    return PHONE.sub("[phone]", EMAIL.sub("[email]", text)), found


def detect_sections(text: str) -> dict[str, bool]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    present = {k: False for k in SECTIONS}
    for ln in lines:
        if len(ln) > 45:
            continue
        clean = re.sub(r"[^A-Za-z /&\-]", " ", ln).strip()
        for k, pat in _HEADING.items():
            if pat.match(clean):
                present[k] = True
    return present


def parse_resume(filename: str, data: bytes) -> ParsedResume:
    raw, kind, pages = extract_text(filename, data)
    text, has_contact = redact(raw)
    words = len(re.findall(r"[A-Za-z]{2,}", text))
    sections = detect_sections(text)
    warnings = []
    if words < 80:
        warnings.append("Almost no text could be read. If this is a scanned or image-based resume, ATS software "
                        "can't read it either: export a text-based PDF from Word or Google Docs.")
    elif words < 200:
        warnings.append("Very short resume: add projects, internships and measurable results.")
    if words > 1100:
        warnings.append("Long resume: for freshers and early-career roles in India, 1 page (~450–650 words) is "
                        "the norm; recruiters skim.")
    if not has_contact:
        warnings.append("No email or phone number found: recruiters and ATS need a way to contact you.")
    for sec, label in (("experience", "Experience/Internships"), ("education", "Education"), ("skills", "Skills")):
        if not sections[sec]:
            warnings.append(f"No '{label}' heading detected: use standard section headings so ATS can parse them.")
    return ParsedResume(text=text, kind=kind, pages=pages, word_count=words, skills=extract_skills(text),
                        sections=sections, has_contact=has_contact, warnings=warnings)


def from_row(r) -> ParsedResume:
    """models.Resume -> ParsedResume (kept here so routers and the agent share it)."""
    return ParsedResume(text=r.text, kind=r.kind, pages=r.pages, word_count=r.word_count, skills=r.skills,
                        sections=r.sections, has_contact=r.has_contact, warnings=r.warnings)
