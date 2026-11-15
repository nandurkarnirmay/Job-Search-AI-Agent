"use client";
import { useState } from "react";
import type { BandStats, CareerPath, GitHubReport, NegotiationAdvice, RoadmapStep } from "@/lib/api";
import { safeUrl } from "@/lib/api";

const VERDICT: Record<NegotiationAdvice["verdict"], string> = {
  "below market": "bg-amber-50 text-amber-900 border-amber-200",
  "around market": "bg-slate-50 text-slate-800 border-slate-200",
  "above market": "bg-green-50 text-green-900 border-green-200",
  "no data": "bg-slate-50 text-slate-600 border-slate-200",
};

export function NegotiationCard({ a }: { a: NegotiationAdvice }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(a.script);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="font-semibold">Offer: ₹{a.offer_lpa} LPA · {a.role}{a.city ? ` · ${a.city}` : ""}</h3>
        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${VERDICT[a.verdict]}`}>{a.verdict}</span>
        {a.counter_lpa != null && (
          <span className="rounded bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">Counter: ₹{a.counter_lpa} LPA</span>
        )}
      </div>
      {a.benchmark && (
        <p className="text-slate-600">
          Benchmark ({a.benchmark_source}, n={a.benchmark.n}): median ₹{a.benchmark.median} LPA, middle half
          ₹{a.benchmark.p25}–{a.benchmark.p75} LPA. Your offer is around the {a.offer_percentile}th percentile.
        </p>
      )}
      {a.talking_points.length > 0 && <ul className="list-disc space-y-1 pl-5">{a.talking_points.map((p) => <li key={p}>{p}</li>)}</ul>}
      <details className="rounded bg-slate-50 p-3">
        <summary className="cursor-pointer font-medium">Email draft</summary>
        <pre className="mt-2 whitespace-pre-wrap font-sans">{a.script}</pre>
        <button onClick={copy} className="mt-2 rounded border border-slate-300 px-2 py-1 text-xs hover:bg-white">
          {copied ? "Copied ✓" : "Copy"}
        </button>
      </details>
      <details className="rounded bg-slate-50 p-3">
        <summary className="cursor-pointer font-medium">Before you accept: CTC checklist</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5">{a.checklist.map((c) => <li key={c}>{c}</li>)}</ul>
      </details>
      {a.notes.map((n) => <p key={n} className="text-xs text-slate-500">{n}</p>)}
    </div>
  );
}

/** Salary by required experience: one horizontal bar per band (median), single hue, value labelled. */
export function BandsChart({ bands }: { bands: BandStats[] }) {
  const max = Math.max(...bands.map((b) => b.stats?.max ?? 0), 1);
  return (
    <div className="space-y-1.5" role="table" aria-label="Median advertised salary by required experience">
      {bands.map((b) => (
        <div key={b.band} role="row" className="flex items-center gap-2 text-sm">
          <span role="cell" className="w-32 shrink-0 text-slate-600">{b.label}</span>
          <div role="cell" className="relative h-4 flex-1 rounded bg-slate-100">
            {b.stats && (
              <>
                <div className="absolute inset-y-1 rounded bg-blue-200" title={`Middle half ₹${b.stats.p25}–${b.stats.p75} LPA`}
                  style={{ left: `${(b.stats.p25 / max) * 100}%`, width: `${((b.stats.p75 - b.stats.p25) / max) * 100}%` }} />
                <div className="absolute inset-y-0 w-1 rounded bg-blue-700" title={`Median ₹${b.stats.median} LPA (n=${b.stats.n})`}
                  style={{ left: `calc(${(b.stats.median / max) * 100}% - 2px)` }} />
              </>
            )}
          </div>
          <span role="cell" className="w-36 shrink-0 text-right text-xs text-slate-600">
            {b.stats ? `₹${b.stats.median} LPA · n=${b.stats.n}` : b.n ? `only ${b.n} salaries` : "no data"}
          </span>
        </div>
      ))}
      <p className="text-xs text-slate-500">Dark mark = median, light band = middle half of advertised salaries.</p>
    </div>
  );
}

const STATUS_NEXT: Record<RoadmapStep["status"], RoadmapStep["status"]> = { todo: "learning", learning: "done", done: "todo" };
const STATUS_LABEL: Record<RoadmapStep["status"], string> = { todo: "To do", learning: "Learning", done: "Done ✓" };

export function CareerCard({ p, onStatus }: { p: CareerPath; onStatus?: (skill: string, s: RoadmapStep["status"]) => void }) {
  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 text-sm">
      <h3 className="font-semibold">Career path: {p.role}</h3>
      {p.ladder.length > 0 && (
        <ol className="flex flex-wrap items-center gap-2">
          {p.ladder.map((s, i) => (
            <li key={s.title} className="flex items-center gap-2">
              <span className="rounded border border-slate-200 bg-slate-50 px-2 py-1">{s.title} <span className="text-xs text-slate-500">{s.years} yrs</span></span>
              {i < p.ladder.length - 1 && <span aria-hidden className="text-slate-400">→</span>}
            </li>
          ))}
        </ol>
      )}
      {p.have.length > 0 && <p><span className="text-slate-600">You already show:</span> {p.have.join(", ")}</p>}
      {p.phases.map((phase, i) => (
        <div key={i} className="space-y-2">
          <h4 className="font-medium">Phase {i + 1} · ~{phase.reduce((n, s) => n + s.weeks, 0)} weeks</h4>
          {phase.map((s) => (
            <div key={s.skill} className="rounded border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{s.skill}
                  {s.demand_share != null && <span className="ml-2 text-xs text-slate-500">in {Math.round(s.demand_share * 100)}% of postings</span>}
                </span>
                {onStatus ? (
                  <button onClick={() => onStatus(s.skill, STATUS_NEXT[s.status])}
                    className="rounded border border-slate-300 px-2 py-0.5 text-xs hover:bg-slate-50">{STATUS_LABEL[s.status]}</button>
                ) : <span className="text-xs text-slate-500">{STATUS_LABEL[s.status]}</span>}
              </div>
              {s.resources.map((r) => (
                <a key={r.url + r.title} href={safeUrl(r.url)} target="_blank" rel="noopener noreferrer" className="block text-blue-700">{r.title} ↗</a>
              ))}
              {s.project && <p className="mt-1 text-slate-600"><b>Project:</b> {s.project}</p>}
            </div>
          ))}
        </div>
      ))}
      {p.adjacent_roles.length > 0 && <p className="text-slate-600">Adjacent roles: {p.adjacent_roles.join(", ")}</p>}
      {p.notes.map((n) => <p key={n} className="text-xs text-slate-500">{n}</p>)}
    </div>
  );
}

export function GitHubCard({ r }: { r: GitHubReport }) {
  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 text-sm">
      <div>
        <h3 className="font-semibold"><a href={safeUrl(r.profile_url)} target="_blank" rel="noopener noreferrer" className="text-blue-700">@{r.username}</a>{r.name ? ` · ${r.name}` : ""}</h3>
        <p className="text-slate-600">{r.original_repos} original repos · {r.active_repos_6m} active in 6 months · {r.total_stars} stars · {r.account_years} yrs on GitHub</p>
      </div>
      {Object.keys(r.languages).length > 0 && (
        <p><span className="text-slate-600">Languages:</span> {Object.entries(r.languages).map(([k, v]) => `${k} (${v})`).join(", ")}</p>
      )}
      <ul className="space-y-1">
        {r.checks.map((c) => (
          <li key={c.name}><span className={c.score >= 0.7 ? "text-green-700" : "text-amber-700"}>{c.score >= 0.7 ? "✓" : "△"}</span> <b>{c.name}:</b> {c.comment}</li>
        ))}
      </ul>
      {r.missing_from_resume.length > 0 && <p><b>On GitHub, not on your resume:</b> {r.missing_from_resume.join(", ")}</p>}
      {r.unproven_on_github.length > 0 && <p><b>On your resume, no public project:</b> {r.unproven_on_github.join(", ")}</p>}
      {r.top_repos.length > 0 && (
        <ul className="list-disc pl-5">
          {r.top_repos.map((x) => (
            <li key={x.url}><a href={safeUrl(x.url)} target="_blank" rel="noopener noreferrer" className="text-blue-700">{x.name}</a>
              {x.language ? ` · ${x.language}` : ""}{x.stars ? ` · ★${x.stars}` : ""}{x.description ? ` · ${x.description}` : ""}</li>
          ))}
        </ul>
      )}
      {r.notes.map((n) => <p key={n} className="text-xs text-slate-500">{n}</p>)}
    </div>
  );
}
