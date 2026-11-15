import Link from "next/link";
import type { AppStatus, ATSMatch, InterviewSession, ResumeReview } from "@/lib/api";

const tone = (score: number) => (score >= 75 ? "bg-green-600" : score >= 50 ? "bg-amber-500" : "bg-red-500");

function Chips({ items, cls }: { items: string[]; cls: string }) {
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((s) => <span key={s} className={`rounded px-2 py-0.5 text-xs ${cls}`}>{s}</span>)}
    </div>
  );
}

export function ATSCard({ m }: { m: ATSMatch }) {
  const parts: [string, number, number][] = [["Skills", m.skills_score, 70], ["Title", m.title_score, 15],
    ["Structure", m.structure_score, 15]];
  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-4">
        <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-lg font-bold text-white ${tone(m.score)}`}>
          {m.score}
        </div>
        <div>
          <h3 className="font-semibold">ATS match: {m.job_title}{m.company ? ` · ${m.company}` : ""}</h3>
          <p className="text-xs text-slate-500">{parts.map(([n, v, max]) => `${n} ${v}/${max}`).join(" · ")}</p>
        </div>
      </div>
      {(m.matched_required.length > 0 || m.matched_preferred.length > 0) && (
        <div><p className="mb-1 text-xs font-medium text-slate-600">You show</p>
          <Chips items={[...m.matched_required, ...m.matched_preferred]} cls="bg-green-50 text-green-800" /></div>
      )}
      {m.missing_required.length > 0 && (
        <div><p className="mb-1 text-xs font-medium text-slate-600">Missing: required</p>
          <Chips items={m.missing_required} cls="bg-red-50 text-red-800" /></div>
      )}
      {m.missing_preferred.length > 0 && (
        <div><p className="mb-1 text-xs font-medium text-slate-600">Missing: nice to have</p>
          <Chips items={m.missing_preferred} cls="bg-slate-100 text-slate-700" /></div>
      )}
      {m.suggestions.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm">{m.suggestions.map((s) => <li key={s}>{s}</li>)}</ul>
      )}
      {m.notes.map((n) => <p key={n} className="text-xs text-slate-500">{n}</p>)}
    </div>
  );
}

export function ReviewCard({ r }: { r: ResumeReview }) {
  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="font-semibold">Resume review{r.role ? ` for ${r.role}` : ""}</h3>
      {r.warnings.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">{r.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
      )}
      {r.demand.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-slate-600">Most requested in {r.jobs_sampled} current postings</p>
          {r.demand.map((d) => (
            <div key={d.skill} className="flex items-center gap-2 text-sm">
              <span className="w-36 shrink-0 truncate">{d.have ? "✓" : "✗"} {d.skill}</span>
              <div className="h-2 flex-1 rounded bg-slate-100">
                <div className={`h-2 rounded ${d.have ? "bg-green-500" : "bg-red-400"}`} style={{ width: `${d.share * 100}%` }} />
              </div>
              <span className="w-10 text-right text-xs text-slate-500">{Math.round(d.share * 100)}%</span>
            </div>
          ))}
        </div>
      )}
      {r.notes.map((n) => <p key={n} className="text-xs text-slate-500">{n}</p>)}
    </div>
  );
}

export function InterviewCard({ s }: { s: InterviewSession }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="font-semibold">Interview practice: {s.role}{s.company ? ` · ${s.company}` : ""}</h3>
      <p className="text-sm text-slate-600">{s.questions.length} questions: HR, technical and behavioural.</p>
      <Link href={`/interview/${s.id}`} className="mt-2 inline-block rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">
        Start practising →
      </Link>
    </div>
  );
}

export function PipelineBar({ p }: { p: Record<AppStatus, number> }) {
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(p).map(([s, n]) => (
        <Link key={s} href="/applications" className="rounded border border-slate-200 bg-white px-3 py-1 text-sm">
          <b>{n}</b> <span className="capitalize text-slate-600">{s}</span>
        </Link>
      ))}
    </div>
  );
}
