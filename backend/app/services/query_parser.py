"""Rule-based parser: free text -> SearchParams. Used when no LLM key is set or the LLM call fails,
and as a cross-check for numbers the LLM might hallucinate."""
import re

from app.domain import SearchParams

CITIES = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru", "mumbai": "Mumbai", "bombay": "Mumbai",
    "delhi": "Delhi", "new delhi": "Delhi", "ncr": "Delhi", "gurugram": "Gurugram", "gurgaon": "Gurugram",
    "noida": "Noida", "hyderabad": "Hyderabad", "chennai": "Chennai", "pune": "Pune", "kolkata": "Kolkata",
    "ahmedabad": "Ahmedabad", "jaipur": "Jaipur", "kochi": "Kochi", "coimbatore": "Coimbatore",
    "indore": "Indore", "chandigarh": "Chandigarh", "bhubaneswar": "Bhubaneswar", "nagpur": "Nagpur",
    "lucknow": "Lucknow", "thiruvananthapuram": "Thiruvananthapuram", "trivandrum": "Thiruvananthapuram",
    "visakhapatnam": "Visakhapatnam", "vizag": "Visakhapatnam", "mysuru": "Mysuru", "mysore": "Mysuru",
}

_FILLER = re.compile(
    r"\b(find|show|search|get|give|me|i|am|want|need|looking|for|some|any|a|an|the|jobs?|openings?|roles?|"
    r"positions?|vacanc(?:y|ies)|in|at|near|with|and|please|job|opportunit(?:y|ies)|of|on|based|"
    r"above|over|more|than|minimum|min|atleast|at|least|salary|package|ctc|lpa|lakhs?|lacs?|per|annum|"
    r"years?|yrs?|experience|exp|remote|hybrid|onsite|on-site|wfh|work|from|home|office|fresher|freshers|"
    r"entry|level|immediate|joiner|notice|period|days?|my|is|have|has|who|which|that|to|can|join)\b",
    re.I,
)


def parse_query(text: str) -> SearchParams:
    t = text.lower()
    params: dict = {}

    for alias in sorted(CITIES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", t):
            params["city"] = CITIES[alias]
            t = re.sub(rf"\b{re.escape(alias)}\b", " ", t)
            break

    if m := re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:lpa|lakhs?|lacs?|l\b)", t):
        params["min_salary_lpa"] = float(m.group(1))
        t = t.replace(m.group(0), " ")

    if re.search(r"\b(fresher|freshers|entry[- ]level|graduate)\b", t):
        params["max_experience_years"] = 0
    elif m := re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", t):
        params["max_experience_years"] = float(m.group(1))
        t = t.replace(m.group(0), " ")

    if re.search(r"\bhybrid\b", t):
        params["work_mode"] = "hybrid"
    elif re.search(r"\b(remote|wfh|work from home)\b", t):
        params["work_mode"] = "remote"
    elif re.search(r"\b(on-?site|work from office|wfo)\b", t):
        params["work_mode"] = "onsite"

    if m := re.search(r"(\d{1,3})\s*days?\s*notice|notice(?: period)?(?: of| is)?\s*(\d{1,3})\s*days?", t):
        params["notice_period_days"] = int(m.group(1) or m.group(2))
        t = t.replace(m.group(0), " ")

    keywords = _FILLER.sub(" ", t)
    keywords = re.sub(r"[^a-z0-9+#./ ]", " ", keywords)
    keywords = re.sub(r"\b\d+(\.\d+)?\b", " ", keywords)
    params["keywords"] = " ".join(keywords.split())
    return SearchParams(**params)
