"""The agent's Week 4 tools, end to end through /chat."""
from tests.conftest import job


def chat(client, message, thread_id=None):
    r = client.post("/chat", json={"message": message} | ({"thread_id": thread_id} if thread_id else {}))
    assert r.status_code == 200, r.text
    return r.json()


def setup_jobs(sources):
    sources[0]._jobs = [job(1, title="Data Analyst", company="Infosys",
                            description="Requirements: SQL and Python. Power BI or Tableau. Nice to have: AWS."),
                        job(2, title="Java Developer", company="Zoho", description="Java, Spring Boot, Hibernate")]
    sources[1]._jobs = []


def test_resume_match_needs_resume_then_scores(auth_client, sources, resume_pdf):
    setup_jobs(sources)
    t = chat(auth_client, "data analyst jobs")["thread_id"]
    assert "Upload your resume" in chat(auth_client, "how well does my resume match the first job?", t)["reply"]
    auth_client.post("/resume", files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    data = chat(auth_client, "how well does my resume match the first job?", t)
    ats = data["extras"]["ats"]
    assert data["intent"] == "resume_match" and ats["job_title"] == "Data Analyst"
    assert ats["missing_required"] == [] and ats["missing_preferred"] == ["AWS"]
    worse = chat(auth_client, "ATS score for the second job", t)["extras"]["ats"]
    assert worse["score"] < ats["score"] and "Java" in worse["missing_required"]


def test_save_and_pipeline_via_chat(auth_client, sources):
    setup_jobs(sources)
    t = chat(auth_client, "data analyst jobs")["thread_id"]
    saved = chat(auth_client, "save the second job", t)
    assert saved["intent"] == "track_application" and saved["extras"]["application"]["company"] == "Zoho"
    assert "Already in your tracker" in chat(auth_client, "save the second job", t)["reply"]
    p = chat(auth_client, "show my applications", t)
    assert p["extras"]["pipeline"]["saved"] == 1
    assert len(auth_client.get("/applications").json()) == 1


def test_interview_prep_via_chat_creates_practice_session(auth_client, sources):
    setup_jobs(sources)
    t = chat(auth_client, "data analyst jobs")["thread_id"]
    data = chat(auth_client, "prepare me for the first job interview", t)
    iv = data["extras"]["interview"]
    assert data["intent"] == "interview_prep" and iv["company"] == "Infosys"
    assert any(q["skill"] == "SQL" for q in iv["questions"])
    assert auth_client.get(f"/interview/sessions/{iv['id']}").status_code == 200


def test_cards_survive_reloading_the_conversation(auth_client, sources):
    setup_jobs(sources)
    t = chat(auth_client, "data analyst jobs")["thread_id"]
    chat(auth_client, "save the first job", t)
    msgs = auth_client.get(f"/chat/threads/{t}").json()["messages"]
    assert msgs[-1]["payload"]["extras"]["application"]["title"] == "Data Analyst"


def test_filter_removal_via_chat(auth_client, sources):
    t = chat(auth_client, "python developer jobs in Bangalore above 8 lpa")["thread_id"]
    data = chat(auth_client, "remove the salary filter", t)
    assert data["intent"] == "refine_search" and data["params"]["min_salary_lpa"] is None
    assert data["params"]["city"] == "Bengaluru"
