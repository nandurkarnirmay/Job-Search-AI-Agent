import pytest

from app.agent.router import extract_company, route
from app.domain import SearchParams

LAST = SearchParams(keywords="python developer", city="Bengaluru")
JOBS = [{"id": "1", "title": "Python Developer", "company": "Infosys", "location": "Bengaluru, Karnataka", "url": "u"},
        {"id": "2", "title": "Backend Engineer", "company": "Zoho", "location": "Chennai, Tamil Nadu", "url": "u"}]


@pytest.mark.parametrize("message,intent", [
    ("hi", "help"),
    ("show me jobs", "help"),
    ("remote python developer jobs in Bangalore above 8 LPA", "job_search"),
    ("python jobs with salary above 8 lpa", "job_search"),        # a filter, not a salary question
    ("tell me about python jobs in pune", "job_search"),           # not a company called "python jobs"
    ("tell me about Infosys", "company_research"),
    ("what is it like working at Swiggy", "company_research"),
    ("is Zoho a good company for freshers", "company_research"),
    ("Flipkart company details", "company_research"),
    ("average salary of data analyst in pune", "salary_research"),
    ("how much do devops engineers earn", "salary_research"),
    ("what about Pune?", "refine_search"),
    ("only remote", "refine_search"),
    ("show more", "refine_search"),
])
def test_intents(message, intent):
    assert route(message, last_params=LAST, last_jobs=JOBS).intent == intent


def test_refine_merges_with_previous_search():
    r = route("what about Pune? above 12 lpa", last_params=LAST)
    assert r.params.model_dump(include={"keywords", "city", "min_salary_lpa"}) == \
        {"keywords": "python developer", "city": "Pune", "min_salary_lpa": 12.0}
    assert route("show more", last_params=LAST).params.page == 2


def test_refine_needs_a_previous_search():
    assert route("what about Pune?").intent == "help"


@pytest.mark.parametrize("message,company", [
    ("tell me about the second company", "Zoho"),
    ("tell me about the last one", "Zoho"),
    ("info on #1", "Infosys"),
])
def test_ordinal_references(message, company):
    r = route(message, last_params=LAST, last_jobs=JOBS)
    assert (r.intent, r.company) == ("company_research", company)


def test_salary_of_an_earlier_result():
    r = route("what's the salary of the 2nd job", last_params=LAST, last_jobs=JOBS)
    assert r.intent == "salary_research"
    assert (r.params.keywords, r.params.city) == ("Backend Engineer", "Chennai")


def test_ordinal_out_of_range_asks_instead_of_guessing():
    r = route("tell me about the fifth company", last_jobs=JOBS)
    assert r.intent == "help" and "2 result" in r.notes[0]
    assert route("tell me about the second company").intent == "help"   # no previous search at all


def test_profile_target_role_used_for_generic_search():
    r = route("show me jobs", default_keywords="data analyst")
    assert (r.intent, r.params.keywords) == ("job_search", "data analyst")


def test_unmatched_message_is_not_confident():
    assert route("which is better for my career growth honestly").confident is False


@pytest.mark.parametrize("message,name", [
    ("Tell me about the company TCS?", "TCS"),
    ("research Zomato please", "Zomato"),
    ("tell me about it", None),
    ("tell me about remote jobs", None),
])
def test_extract_company(message, name):
    assert extract_company(message) == name


# ---------- Week 4 ----------
LAST4 = SearchParams(keywords="python developer", city="Bengaluru", min_salary_lpa=8, work_mode="remote")


@pytest.mark.parametrize("message,intent", [
    ("save the second job", "track_application"),
    ("add #1 to my tracker", "track_application"),
    ("how well does my resume match the second job", "resume_match"),
    ("ATS score for #1", "resume_match"),
    ("prepare me for the first job interview", "interview_prep"),
    ("review my resume for data analyst roles", "resume_review"),
    ("what skills am I missing for data engineer", "resume_review"),
    ("interview questions for a data analyst", "interview_prep"),
    ("show my applications", "applications_status"),
    ("save it", "help"),
])
def test_week4_intents(message, intent):
    assert route(message, last_params=LAST4, last_jobs=JOBS).intent == intent


@pytest.mark.parametrize("message,expected", [
    ("remove the salary filter", {"keywords": "python developer", "city": "Bengaluru", "work_mode": "remote"}),
    ("any city", {"keywords": "python developer", "min_salary_lpa": 8.0, "work_mode": "remote"}),
    ("clear filters", {"keywords": "python developer"}),
    ("not only remote", {"keywords": "python developer", "city": "Bengaluru", "min_salary_lpa": 8.0}),
    ("remove the remote filter, show hybrid",
     {"keywords": "python developer", "city": "Bengaluru", "min_salary_lpa": 8.0, "work_mode": "hybrid"}),
    ("any city but above 12 lpa", {"keywords": "python developer", "min_salary_lpa": 12.0, "work_mode": "remote"}),
])
def test_filter_removal(message, expected):
    r = route(message, last_params=LAST4)
    assert r.intent == "refine_search"
    assert r.params.model_dump(exclude_none=True, exclude={"page"}) == expected


def test_new_role_with_removal_is_a_new_search():
    r = route("java jobs anywhere", last_params=LAST4)
    assert r.intent == "job_search" and r.params.keywords == "java" and r.params.city is None


def test_interview_role_and_company_extraction():
    r = route("mock interview for Python developer at Infosys")
    assert (r.role, r.company) == ("python developer", "Infosys")
    assert route("interview tips").intent == "help"                         # no role anywhere
    assert route("interview tips", default_keywords="data analyst").role == "data analyst"
