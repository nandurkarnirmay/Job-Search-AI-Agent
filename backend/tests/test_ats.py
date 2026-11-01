import pytest

from app.domain import ParsedResume
from app.services.resume_analysis import ats_match, classify_job_skills
from app.services.skills import extract_skills


@pytest.mark.parametrize("text,expected,absent", [
    ("Java, Spring Boot and MySQL", {"Java", "Spring Boot", "MySQL", "SQL"}, {"JavaScript"}),
    ("JavaScript and TypeScript", {"JavaScript", "TypeScript"}, {"Java"}),
    ("C++, C# and .NET", {"C++", "C#", ".NET"}, {"C"}),
    ("replaced spark plugs; rust-proof coatings; spring internship", set(), {"Spark", "Rust", "Spring"}),
    ("Spark and Hadoop pipelines", {"Spark", "Hadoop"}, set()),
    ("Go to market with C-level executives in R&D", set(), {"Go", "C", "R"}),
    ("SolidWorks, ANSYS Fluent CFD, GD&T", {"SolidWorks", "ANSYS", "CFD", "GD&T"}, set()),
])
def test_skill_extraction(text, expected, absent):
    found = set(extract_skills(text))
    assert expected <= found and not (absent & found)


def test_alternatives_and_preferred():
    req, pref = classify_job_skills(
        "Strong SQL. Dashboards in Power BI or Tableau. Knowledge of Java, Scala or Go language.\n"
        "Nice to have: AWS. Experience with Docker is a plus.")
    assert ["Power BI", "Tableau"] in req and ["Java", "Scala", "Go"] in req and ["SQL"] in req
    assert ["AWS"] in pref and ["Docker"] in pref


def resume(text, sections=("experience", "education", "skills", "projects"), contact=True):
    return ParsedResume(text=text, kind="pdf", word_count=300, skills=extract_skills(text),
                        sections={s: s in sections for s in ("experience", "education", "skills", "projects")},
                        has_contact=contact)


def test_score_is_transparent_and_rewards_matches():
    jd = "Must have SQL and Python. Power BI or Tableau. Nice to have: Airflow."
    strong = ats_match(resume("Data Analyst. Python, SQL, Tableau, Airflow"), "Data Analyst", jd)
    weak = ats_match(resume("Mechanical engineer. SolidWorks", sections=("education",), contact=False),
                     "Data Analyst", jd)
    assert strong.score == 100 and strong.missing_required == []
    assert weak.score < 20 and set(weak.missing_required) == {"SQL", "Python", "Power BI or Tableau"}
    assert round(weak.skills_score + weak.title_score + weak.structure_score) == weak.score


def test_no_skills_in_posting_is_low_confidence():
    m = ats_match(resume("Python"), "Office Executive", "Looking for a hardworking and punctual person.")
    assert any("rough indicator" in n for n in m.notes)


def test_suggestions_never_tell_you_to_add_skills_you_lack_unconditionally():
    m = ats_match(resume("Python"), "Java Developer", "Must have Java.")
    assert all("genuinely" in s for s in m.suggestions if "asks for" in s)
