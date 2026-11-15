"""Percentiles in LPA from raw values or from a bucketed histogram. Pure functions."""
import math

from app.domain import JobListing, SalaryStats
from app.sources.normalize import LAKH

MIN_LISTINGS = 3          # fewer disclosed salaries than this is an anecdote, not a statistic
MIN_HISTOGRAM_COUNT = 10
SANE_LPA = (0.5, 200.0)   # drops parse errors such as a monthly figure read as yearly


def percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        raise ValueError("empty")
    k = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def _r(x: float) -> float:
    return round(x, 1)


def stats_from_values(values: list[float], min_n: int = MIN_LISTINGS) -> SalaryStats | None:
    vals = sorted(v for v in values if SANE_LPA[0] <= v <= SANE_LPA[1])
    if len(vals) < min_n:
        return None
    return SalaryStats(n=len(vals), p25=_r(percentile(vals, 0.25)), median=_r(percentile(vals, 0.5)),
                       p75=_r(percentile(vals, 0.75)), min=_r(vals[0]), max=_r(vals[-1]))


def job_salary_midpoint(job: JobListing) -> float | None:
    lo, hi = job.salary_min_lpa, job.salary_max_lpa
    if lo is None and hi is None:
        return None
    if lo is None or hi is None:
        return lo if hi is None else hi
    return (lo + hi) / 2


def stats_from_histogram(hist: dict[float, int], min_count: int = MIN_HISTOGRAM_COUNT) -> SalaryStats | None:
    """hist = {bucket_lower_bound_inr: count}. Assumes values are spread evenly inside each bucket."""
    buckets = sorted((lb, c) for lb, c in hist.items() if c > 0)
    total = sum(c for _, c in buckets)
    if total < min_count:
        return None
    bounds = [lb for lb, _ in buckets]
    widths = [bounds[i + 1] - bounds[i] for i in range(len(bounds) - 1)]
    widths.append(widths[-1] if widths else 0.0)  # last bucket: assume the same width as the previous one

    def q(p: float) -> float:
        target, cum = p * total, 0
        for (lb, c), w in zip(buckets, widths, strict=True):
            if cum + c >= target:
                return (lb + w * (target - cum) / c) / LAKH
            cum += c
        return (bounds[-1] + widths[-1]) / LAKH

    return SalaryStats(n=total, p25=_r(q(0.25)), median=_r(q(0.5)), p75=_r(q(0.75)),
                       min=_r(bounds[0] / LAKH), max=_r((bounds[-1] + widths[-1]) / LAKH))


def fmt_lpa(x: float) -> str:
    return f"₹{x:g} LPA"


def describe(stats: SalaryStats) -> str:
    return (f"median {fmt_lpa(stats.median)}, middle half ₹{stats.p25:g}–{stats.p75:g} LPA, "
            f"range ₹{stats.min:g}–{stats.max:g} LPA")
