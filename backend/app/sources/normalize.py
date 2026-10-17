"""Turn messy Indian job-listing text into structured fields. Pure functions: easy to unit-test."""
import hashlib
import re

LAKH = 100_000

_NUM = r"(\d+(?:\.\d+)?)"
_LPA_RANGE = re.compile(_NUM + r"\s*(?:-|to|–)\s*" + _NUM + r"\s*(?:lpa|lakhs?|l\b|lacs?)", re.I)
_LPA_SINGLE = re.compile(_NUM + r"\s*(?:lpa|lakhs? per annum|lakhs?|lacs?)", re.I)
_EXP_RANGE = re.compile(_NUM + r"\s*(?:-|to|–)\s*" + _NUM + r"\s*(?:\+\s*)?(?:years?|yrs?)", re.I)
_EXP_MIN = re.compile(r"(?:minimum|min\.?|at least)?\s*" + _NUM + r"\s*\+?\s*(?:years?|yrs?)", re.I)
_NOTICE = re.compile(r"notice period[^\d]{0,30}(\d{1,3})\s*days", re.I)
_IMMEDIATE = re.compile(r"immediate(?:ly)?\s*(?:joiner|joining|join)", re.I)
_FRESHER = re.compile(r"\bfreshers?\b", re.I)


def rupees_to_lpa(amount: float | None, period: str | None = "year") -> float | None:
    if amount is None or amount <= 0:
        return None
    period = (period or "year").lower()
    yearly = {"year": amount, "month": amount * 12}.get(period)
    if yearly is None:  # hourly/daily salaries are not comparable reliably
        return None
    return round(yearly / LAKH, 2)


def salary_lpa_from_text(text: str) -> tuple[float | None, float | None]:
    if m := _LPA_RANGE.search(text):
        lo, hi = float(m.group(1)), float(m.group(2))
        return (min(lo, hi), max(lo, hi))
    if m := _LPA_SINGLE.search(text):
        v = float(m.group(1))
        return (v, v)
    return (None, None)


def experience_from_text(text: str) -> tuple[float | None, float | None]:
    if _FRESHER.search(text):
        return (0.0, 1.0)
    if m := _EXP_RANGE.search(text):
        lo, hi = float(m.group(1)), float(m.group(2))
        if hi <= 40:
            return (min(lo, hi), max(lo, hi))
    if m := _EXP_MIN.search(text):
        v = float(m.group(1))
        if v <= 40:
            return (v, None)
    return (None, None)


def notice_period_from_text(text: str) -> int | None:
    if _IMMEDIATE.search(text):
        return 0
    if m := _NOTICE.search(text):
        return int(m.group(1))
    return None


def work_mode_from_text(text: str, is_remote_flag: bool | None = None) -> str | None:
    t = text.lower()
    if "hybrid" in t:
        return "hybrid"
    if is_remote_flag or re.search(r"\b(remote|work from home|wfh)\b", t):
        return "remote"
    if re.search(r"\b(on-?site|work from office|wfo|in-office)\b", t):
        return "onsite"
    return None


def canonical_city(city: str) -> str:
    aliases = {"bangalore": "bengaluru", "gurgaon": "gurugram", "bombay": "mumbai", "madras": "chennai",
               "calcutta": "kolkata", "new delhi": "delhi", "delhi ncr": "delhi"}
    c = city.strip().lower()
    return aliases.get(c, c)


def dedupe_key(title: str, company: str, location: str) -> str:
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    city = canonical_city(location.split(",")[0]) if location else ""
    return hashlib.sha1(f"{norm(title)}|{norm(company)}|{norm(city)}".encode()).hexdigest()[:16]
