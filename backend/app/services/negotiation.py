"""Offer evaluation and negotiation help. Every number comes from the benchmark and fixed rules below,
never from an LLM, so the advice is reproducible and can be explained line by line.

Rules (offer position within the benchmark distribution -> counter):
  below p25          -> counter at the median                      ("below market")
  p25 .. median      -> counter halfway between median and p75     ("around market")
  median .. p75      -> counter at offer + 8%                      ("around market")
  above p75          -> no cash counter; negotiate joining bonus, notice buyout, WFH, learning budget
A competing higher offer raises the counter to at least that offer. Counters are at least offer + 5%, rounded
UP to ₹0.5 LPA (so they never land below the target), and capped at offer + 25% (beyond that a counter rarely
stays credible) unless a competing offer is higher than that."""
import math
import re

from app.domain import NegotiationAdvice, SalaryStats, SearchParams
from app.services.salary_research import band_for, research_salary

CHECKLIST = [
    "Ask for the CTC breakdown in writing: fixed pay vs variable/performance pay, and how often variable is paid.",
    "Check what's inside the CTC: employer PF, gratuity and insurance premiums are often included, so in-hand "
    "pay is lower than CTC ÷ 12.",
    "Joining bonus: is it paid with the first salary, and is there a clawback if you leave within 12 months?",
    "ESOPs/RSUs: vesting schedule, cliff, and what happens if you leave early.",
    "Probation length, notice period after confirmation, and whether the company buys out your current notice.",
    "Relocation support, work-from-home/hybrid policy and learning or certification budget.",
]


def percentile_of(value: float, s: SalaryStats) -> int:
    """Approximate percentile of value by linear interpolation through min/p25/median/p75/max."""
    points = [(s.min, 0), (s.p25, 25), (s.median, 50), (s.p75, 75), (s.max, 100)]
    if value <= points[0][0]:
        return 0
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if value <= x1:
            return round(y0 + (y1 - y0) * ((value - x0) / (x1 - x0) if x1 > x0 else 1))
    return 100


def _up_half(x: float) -> float:
    return math.ceil(round(x * 2, 6)) / 2


def _down_half(x: float) -> float:
    return math.floor(round(x * 2, 6)) / 2


def advise(role: str, offer_lpa: float, *, city: str | None = None, experience_years: float | None = None,
           current_lpa: float | None = None, competing_lpa: float | None = None,
           notice_period_days: int | None = None, skills: list[str] | None = None,
           name: str | None = None) -> NegotiationAdvice:
    report = research_salary(SearchParams(keywords=role, city=city, max_experience_years=experience_years))
    a = NegotiationAdvice(role=role, city=city, experience_years=experience_years, offer_lpa=offer_lpa,
                          checklist=CHECKLIST, notes=list(report.notes))

    band = next((b for b in report.bands if experience_years is not None and b.band == band_for(experience_years)
                 and b.stats), None)
    if band:
        a.benchmark, a.benchmark_source = band.stats, f"current listings for {band.label} experience"
    elif report.listings:
        a.benchmark, a.benchmark_source = report.listings, "current listings for this role"
    elif report.market:
        a.benchmark, a.benchmark_source = report.market, "Adzuna market estimate (includes estimated salaries)"

    if current_lpa:
        a.hike_pct = round((offer_lpa / current_lpa - 1) * 100, 1)

    target = None
    if a.benchmark:
        s = a.benchmark
        a.offer_percentile = percentile_of(offer_lpa, s)
        if a.offer_percentile < 25:
            a.verdict, target = "below market", s.median
        elif offer_lpa < s.median:
            a.verdict, target = "around market", (s.median + s.p75) / 2
        elif offer_lpa <= s.p75:
            a.verdict, target = "around market", offer_lpa * 1.08
        else:
            a.verdict = "above market"
        a.talking_points.append(
            f"Your offer of ₹{offer_lpa:g} LPA is around the {a.offer_percentile}th percentile of {a.benchmark_source} "
            f"(median ₹{s.median:g} LPA, middle half ₹{s.p25:g}–{s.p75:g} LPA, n={s.n}).")
    else:
        a.notes.append("Not enough salary data for this role to benchmark the offer. Check AmbitionBox/Glassdoor "
                       "salaries for the same company and role before negotiating.")

    if competing_lpa and competing_lpa > offer_lpa:
        target = max(target or 0, competing_lpa)
        a.talking_points.append(f"You hold a competing offer of ₹{competing_lpa:g} LPA: mention it factually, and say "
                                "which company you'd prefer if the numbers were close.")
    if target is not None:
        cap = max(_down_half(offer_lpa * 1.25), competing_lpa or 0)
        a.counter_lpa = min(_up_half(max(target, offer_lpa * 1.05)), cap)
        if target > cap:
            a.notes.append("The market gap is larger than a single counter can credibly close (capped at +25%); "
                           "consider whether the role's level matches your experience.")
    elif a.verdict == "above market":
        a.talking_points.append("The cash offer is already strong: negotiate the rest of the package instead "
                                "(joining bonus, notice buyout, WFH, learning budget).")

    if a.hike_pct is not None:
        a.talking_points.append(f"The offer is {a.hike_pct:+g}% vs your current CTC of ₹{current_lpa:g} LPA. "
                                "Anchor the discussion on market data and the role, not on your current salary.")
    if notice_period_days and notice_period_days >= 60:
        a.talking_points.append(f"Your notice period is {notice_period_days} days: ask whether they offer a notice "
                                "buyout or a joining date that fits it.")
    if skills:
        a.talking_points.append(f"Tie the ask to value: name the skills that match the role ({', '.join(skills[:3])}) "
                                "and one result from your projects or internship.")
    a.script = _script(a, competing_lpa, notice_period_days, skills, name)
    return a


def _script(a: NegotiationAdvice, competing: float | None, notice: int | None, skills: list[str] | None,
            name: str | None) -> str:
    where = f" in {a.city}" if a.city else ""
    lines = ["Hi [Recruiter's name],", "",
             f"Thank you for the offer for the {a.role} role. I'm excited about the work and the team."]
    if a.counter_lpa:
        basis = (f"Based on current market data for {a.role} roles{where} (median around ₹{a.benchmark.median:g} LPA)"
                 if a.benchmark else "Based on my research for similar roles")
        skill_part = f" and my experience with {', '.join(skills[:3])}" if skills else ""
        lines.append(f"{basis}{skill_part}, I'd like to ask whether the fixed CTC could be revised to "
                     f"₹{a.counter_lpa:g} LPA.")
    else:
        lines.append("I'm happy with the overall compensation and would like to discuss a few parts of the package: "
                     "a joining bonus and the joining date.")
    if competing and competing > a.offer_lpa:
        lines.append(f"For transparency, I have another offer at ₹{competing:g} LPA, but this role is my first "
                     "choice and I'd like to make it work.")
    if notice and notice >= 60:
        lines.append(f"My current notice period is {notice} days; could the company support a notice buyout?")
    lines += ["", "I'm keen to join and happy to discuss.", "", "Regards,", name or "[Your name]"]
    return "\n".join(lines)


# ---------- chat parsing ----------
_LPA = r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lpa|l\b|lakhs?|lacs?)"
_OFFER = re.compile(r"offer(?:ed)?\s*(?:of|is|for|at|:)?\s*" + _LPA + r"|" + _LPA + r"\s*(?:ctc\s*)?offer", re.I)
_CURRENT = re.compile(r"current(?:ly)?\s*(?:ctc|salary|package|pay)?\s*(?:is|of|:)?\s*(?:drawing|earning|getting)?\s*"
                      + _LPA, re.I)
_COMPETING = re.compile(r"(?:another|competing|other|second)\s+offer\s*(?:of|is|for|at|:)?\s*" + _LPA, re.I)


def parse_offer_message(message: str) -> dict:
    """'Got an offer of 8 LPA, current CTC 6 LPA, another offer 9 LPA' -> {offer: 8, current: 6, competing: 9}."""
    out: dict = {}
    if m := _COMPETING.search(message):
        out["competing_lpa"] = float(m.group(1))
        message = message.replace(m.group(0), " ")
    if m := _CURRENT.search(message):
        out["current_lpa"] = float(m.group(1))
        message = message.replace(m.group(0), " ")
    if m := _OFFER.search(message):
        out["offer_lpa"] = float(m.group(1) or m.group(2))
    elif nums := re.findall(_LPA, message, re.I):
        out["offer_lpa"] = float(nums[0])
    return out


def negotiation_reply(a: NegotiationAdvice) -> str:
    lines = [f"Offer check: ₹{a.offer_lpa:g} LPA for {a.role}{' in ' + a.city if a.city else ''}: {a.verdict}."]
    if a.counter_lpa:
        lines.append(f"Suggested counter: ₹{a.counter_lpa:g} LPA (fixed CTC).")
    lines += [f"• {p}" for p in a.talking_points]
    lines += a.notes
    lines.append("\nA ready-to-send email draft and a CTC checklist are in the card below.")
    return "\n".join(lines)
