import pytest

from app.domain import JobListing, SearchParams
from app.services.filters import apply_filters
from app.services.query_parser import parse_query
from app.sources import normalize as nz


@pytest.mark.parametrize("text,expected", [
    ("remote python developer jobs in Bangalore above 8 LPA",
     {"keywords": "python developer", "city": "Bengaluru", "min_salary_lpa": 8.0, "work_mode": "remote"}),
    ("fresher data analyst openings in pune", {"keywords": "data analyst", "city": "Pune", "max_experience_years": 0}),
    ("react developer 3 years hybrid gurgaon 90 days notice",
     {"keywords": "react developer", "city": "Gurugram", "max_experience_years": 3.0, "work_mode": "hybrid",
      "notice_period_days": 90}),
    ("Senior C++ engineer Hyderabad 25 lakhs", {"keywords": "senior c++ engineer", "min_salary_lpa": 25.0}),
])
def test_parse_query(text, expected):
    got = parse_query(text).model_dump()
    for k, v in expected.items():
        assert got[k] == v, k


def test_text_extractors():
    assert nz.salary_lpa_from_text("CTC: 6 - 9 LPA") == (6.0, 9.0)
    assert nz.experience_from_text("Experience: 3+ years") == (3.0, None)
    assert nz.notice_period_from_text("Notice period up to 30 days") == 30
    assert nz.rupees_to_lpa(50000, "month") == 6.0 and nz.rupees_to_lpa(500, "hour") is None
    assert nz.dedupe_key("Python Dev", "Infosys", "Bangalore") == nz.dedupe_key("python dev", "INFOSYS", "Bengaluru")


def test_notice_period_filter_hides_immediate_joiner_jobs():
    jobs = [JobListing(id="1", title="a", company="c", location="Pune", url="u", source="s", notice_period_days=0),
            JobListing(id="2", title="b", company="c", location="Pune", url="u", source="s")]
    kept = apply_filters(jobs, SearchParams(keywords="a", notice_period_days=60))
    assert [j.id for j in kept] == ["2"]
