import io
import zipfile

import pytest
from docx import Document

from tests.conftest import FIXTURES, job, register

from app.services.resume_parser import ResumeError, parse_resume


def docx_bytes(build) -> bytes:
    d = Document()
    build(d)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ---------- parsing (real files, no mocks) ----------

def test_pdf_parsing_skills_sections_and_redaction(resume_pdf):
    r = parse_resume("cv.pdf", resume_pdf)
    assert r.kind == "pdf" and r.pages == 1
    assert {"Python", "SQL", "PostgreSQL", "Power BI", "Docker"} <= set(r.skills)
    assert all(r.sections[s] for s in ("experience", "education", "skills", "projects"))
    assert r.has_contact
    assert "[email]" in r.text and "[phone]" in r.text
    assert "example.com" not in r.text and "98765" not in r.text   # contact details never stored


def test_scanned_pdf_is_flagged():
    r = parse_resume("scan.pdf", (FIXTURES / "blank_scan.pdf").read_bytes())
    assert r.word_count == 0 and "scanned" in r.warnings[0]


def test_docx_reads_tables():
    def build(d):
        d.add_paragraph("Education")
        d.add_paragraph("B.Tech Mechanical, 2026")
        t = d.add_table(rows=1, cols=2)
        t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Skills", "SolidWorks, ANSYS, GD&T"
    r = parse_resume("cv.docx", docx_bytes(build))
    assert {"SolidWorks", "ANSYS", "GD&T"} <= set(r.skills) and r.sections["skills"] and r.sections["education"]
    assert not r.has_contact and any("contact" in w.lower() for w in r.warnings)


@pytest.mark.parametrize("name,data,msg", [
    ("cv.pdf", b"", "empty"),
    ("cv.txt", b"plain text resume", "PDF or DOCX"),
    ("cv.docx", b"PK\x03\x04not really a zip", "DOCX"),
    ("cv.pdf", b"%PDF-1.4 truncated", "PDF"),
    ("cv.pdf", b"%PDF-" + b"0" * (2 * 1024 * 1024), "2 MB"),
])
def test_bad_files_rejected(name, data, msg):
    with pytest.raises(ResumeError, match=msg):
        parse_resume(name, data)


def test_docx_zip_bomb_rejected():
    raw = docx_bytes(lambda d: d.add_paragraph("hi"))
    buf = io.BytesIO(raw)
    with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/padding.bin", b"\0" * (25 * 1024 * 1024))  # compresses to ~25 KB
    with pytest.raises(ResumeError, match="too large"):
        parse_resume("cv.docx", buf.getvalue())


# ---------- API ----------

def upload(client, data, name="cv.pdf", headers=None):
    return client.post("/resume", files={"file": (name, data, "application/octet-stream")}, headers=headers or {})


def test_upload_get_replace_delete(auth_client, resume_pdf):
    r = upload(auth_client, resume_pdf)
    assert r.status_code == 201 and "Python" in r.json()["skills"]
    assert "text" not in r.json()                                     # resume text isn't echoed back
    docx = docx_bytes(lambda d: d.add_paragraph("Skills\nJava, Spring Boot"))
    assert upload(auth_client, docx, "cv.docx").status_code == 201   # replaces the old one
    assert auth_client.get("/resume").json()["kind"] == "docx"
    assert auth_client.delete("/resume").status_code == 204
    assert auth_client.get("/resume").json()["error"]["code"] == "no_resume"


def test_bad_upload_gives_clean_error(auth_client):
    r = upload(auth_client, b"hello", "cv.txt")
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_resume"


def test_match_by_job_id_and_by_pasted_description(auth_client, resume_pdf, sources):
    upload(auth_client, resume_pdf)
    jd = "Requirements: SQL and Python. Dashboards in Power BI or Tableau. Must know Kafka."
    sources[0]._jobs = [job(50, title="Data Analyst", description=jd)]
    sources[1]._jobs = []
    auth_client.get("/jobs/search", params={"q": "data analyst"})     # puts the job in the cache
    m = auth_client.post("/resume/match", json={"job_id": "fake:50"}).json()
    assert "Kafka" in m["missing_required"] and "Tableau" not in " ".join(m["missing_required"])
    assert 0 < m["score"] <= 100

    m2 = auth_client.post("/resume/match", json={"job_title": "Java Developer", "description":
                          "We need Java, Spring Boot and Hibernate experience. Kubernetes is a plus."}).json()
    assert set(m2["missing_required"]) >= {"Java", "Spring Boot", "Hibernate"} and m2["score"] < m["score"]
    assert auth_client.post("/resume/match", json={"job_id": "fake:999"}).status_code == 404


def test_review_uses_market_demand(auth_client, resume_pdf, sources):
    upload(auth_client, resume_pdf)
    sources[0]._jobs = [job(i, description=d) for i, d in enumerate(
        ["SQL, Excel", "SQL, Tableau", "Excel, Tableau, SQL", "Python, SQL", "Tableau and SQL", "Excel"])]
    sources[1]._jobs = []
    r = auth_client.get("/resume/review", params={"role": "data analyst"}).json()
    demand = {d["skill"]: d for d in r["demand"]}
    assert r["jobs_sampled"] == 6 and demand["SQL"]["have"] is True and demand["Tableau"]["have"] is False


def test_resume_is_private_and_deleted_with_account(client, auth_client, resume_pdf):
    upload(auth_client, resume_pdf)
    other = register(client, "other@example.com")
    assert client.get("/resume", headers=other).status_code == 404
    auth_client.delete("/auth/me")
    from app.db import SessionLocal
    from app.models import Resume
    with SessionLocal() as db:
        assert db.query(Resume).count() == 0
