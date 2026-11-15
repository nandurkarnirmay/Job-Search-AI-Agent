"""Offline accuracy benchmarks (no network, no API keys):
  1. intent routing (rules only, no LLM) on eval/router_eval.jsonl
  2. skill extraction precision/recall on eval/skills_eval.jsonl
Run from backend/:  python -m scripts.eval_accuracy"""
import json
from collections import Counter, defaultdict
from pathlib import Path

from app.agent.router import route
from app.domain import SearchParams
from app.services.skills import extract_skills

ROOT = Path(__file__).resolve().parent.parent / "eval"
LAST = SearchParams(keywords="python developer", city="Bengaluru", min_salary_lpa=8, max_experience_years=2)
LAST_JOBS = [{"id": f"x:{i}", "title": t, "company": c, "location": "Pune", "url": "https://example.com"}
             for i, (t, c) in enumerate([("Data Analyst", "Infosys"), ("Java Developer", "Zoho"),
                                         ("ML Engineer", "Swiggy")])]


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / name).read_text().splitlines() if line.strip()]


def eval_router() -> dict:
    rows = load("router_eval.jsonl")
    per = defaultdict(lambda: [0, 0])
    confusion = Counter()
    for r in rows:
        got = route(r["message"], last_params=LAST if r.get("has_last") else None,
                    last_jobs=LAST_JOBS if r.get("has_last") else None).intent
        per[r["intent"]][1] += 1
        if got == r["intent"]:
            per[r["intent"]][0] += 1
        else:
            confusion[(r["intent"], got, r["message"])] += 1
    correct = sum(c for c, _ in per.values())
    return {"n": len(rows), "accuracy": round(correct / len(rows), 3),
            "per_intent": {k: f"{c}/{n}" for k, (c, n) in sorted(per.items())},
            "errors": [f"{exp} -> {got}: {msg}" for (exp, got, msg) in confusion]}


def eval_skills() -> dict:
    rows = load("skills_eval.jsonl")
    tp = fp = fn = 0
    errors = []
    for r in rows:
        got, exp = set(extract_skills(r["text"], with_implied=False)), set(r["skills"])
        tp, fp, fn = tp + len(got & exp), fp + len(got - exp), fn + len(exp - got)
        if got != exp:
            errors.append(f"{r['text'][:60]}… extra={sorted(got - exp)} missed={sorted(exp - got)}")
    p, rc = tp / (tp + fp) if tp + fp else 1.0, tp / (tp + fn) if tp + fn else 1.0
    return {"n": len(rows), "precision": round(p, 3), "recall": round(rc, 3),
            "f1": round(2 * p * rc / (p + rc), 3) if p + rc else 0.0, "errors": errors}


# CI gate: fail the build if accuracy drops below these (current: router 1.0, skills F1 0.994)
MIN_ROUTER_ACCURACY = 0.95
MIN_SKILLS_F1 = 0.95

if __name__ == "__main__":
    import sys

    result = {"router": eval_router(), "skills": eval_skills()}
    print(json.dumps(result, indent=2))
    if "--check" in sys.argv and (result["router"]["accuracy"] < MIN_ROUTER_ACCURACY
                                  or result["skills"]["f1"] < MIN_SKILLS_F1):
        sys.exit("accuracy below the CI threshold")
