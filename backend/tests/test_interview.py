from tests.conftest import job, register

from app.domain import InterviewQuestion
from app.services.interview import build_questions, evaluate_answer


def test_questions_follow_role_skills_and_company():
    qs, notes = build_questions("Data Analyst", "Infosys", "SQL, Python, Power BI dashboards")
    texts = [q.text for q in qs]
    assert texts[0] == "Tell me about yourself." and "Why do you want to join Infosys?" in texts
    assert {"SQL", "Python", "Power BI"} <= {q.skill for q in qs if q.category == "technical"}
    assert sum(q.category == "behavioural" for q in qs) == 2 and notes == []
    assert [q.id for q in qs] == [f"q{i}" for i in range(1, len(qs) + 1)]
    assert build_questions("Data Analyst", "Infosys", "SQL, Python, Power BI dashboards")[0] == qs  # deterministic


def test_core_engineering_role_gets_core_questions():
    qs, _ = build_questions("Graduate Engineer Trainee", "Reliance", "thermodynamics, heat transfer, piping")
    assert {"Thermodynamics", "Heat Transfer", "Fluid Mechanics"} <= {q.skill for q in qs}


def test_unknown_role_says_so():
    qs, notes = build_questions("Marketing Manager")
    assert notes and all(q.category != "technical" for q in qs)


SQL_Q = InterviewQuestion(id="q1", text="What is the difference between WHERE and HAVING?", category="technical",
                          skill="SQL", key_points=[["WHERE before grouping", r"before (?:the )?group|individual rows"],
                                                   ["HAVING after grouping", r"after (?:the )?group|aggregat"]])
STAR_Q = InterviewQuestion(id="q2", text="Tell me about a time you faced a tight deadline.", category="behavioural")


def test_technical_feedback_checks_key_points():
    weak = evaluate_answer(SQL_Q, "WHERE filters rows.")
    strong = evaluate_answer(SQL_Q, "WHERE filters individual rows before grouping, while HAVING filters after "
                                    "GROUP BY on aggregates like SUM. For example in my project I used HAVING "
                                    "COUNT(*) > 5 to find repeat customers in our sales table.")
    assert weak.score <= 2 and weak.key_points_missed == ["WHERE before grouping", "HAVING after grouping"]
    assert strong.score >= 4 and strong.key_points_missed == []


def test_behavioural_feedback_checks_star_and_ownership():
    vague = evaluate_answer(STAR_Q, "We had a project and we finished it. We worked hard and we were happy.")
    star = evaluate_answer(STAR_Q, "During my internship the weekly sales report took 6 hours to build. I wrote SQL "
                                   "queries and built a Power BI dashboard that refreshed automatically. As a result "
                                   "reporting time dropped by 40% and 12 managers now use it every Monday morning.")
    assert vague.score <= 2 and any("'we'" in t for t in vague.tips)
    assert star.score >= 4 and all(c.score == 1.0 for c in star.criteria if c.name != "Length")


def test_hr_answers_must_be_concrete():
    q = InterviewQuestion(id="q3", text="What are your salary expectations (in LPA), and how did you arrive at that "
                                        "number?", category="hr")
    assert evaluate_answer(q, "As per company norms.").score == 1
    assert evaluate_answer(q, "I am expecting 6-8 LPA, based on market data for analyst roles in Pune and my "
                              "internship experience.").score == 5


def test_session_api_flow_and_privacy(client, auth_client, sources):
    sources[0]._jobs = [job(60, title="Data Analyst", company="Infosys", description="SQL and Python, Power BI")]
    auth_client.get("/jobs/search", params={"q": "data analyst"})
    s = auth_client.post("/interview/sessions", json={"job_id": "fake:60"}).json()
    assert s["role"] == "Data Analyst" and s["company"] == "Infosys" and len(s["questions"]) >= 6

    qid = next(q["id"] for q in s["questions"] if q["skill"] == "SQL")
    r = auth_client.post(f"/interview/sessions/{s['id']}/questions/{qid}/answer",
                         json={"answer": "HAVING filters after grouping on aggregates; WHERE filters rows before."})
    assert r.status_code == 200 and 1 <= r.json()["feedback"]["score"] <= 5
    saved = auth_client.get(f"/interview/sessions/{s['id']}").json()
    assert qid in saved["answers"]

    assert auth_client.post(f"/interview/sessions/{s['id']}/questions/q99/answer",
                            json={"answer": "x"}).status_code == 404
    other = register(client, "other@example.com")
    assert client.get(f"/interview/sessions/{s['id']}", headers=other).status_code == 404
    assert auth_client.post("/interview/sessions", json={}).status_code == 422
