"use client";
import { FormEvent, useEffect, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import { ATSCard, ReviewCard } from "@/components/Week4Cards";
import { api, ApiError, ATSMatch, ResumeInfo, ResumeReview } from "@/lib/api";

const SECTION_LABELS: Record<string, string> = {
  experience: "Experience / internships", education: "Education", skills: "Skills", projects: "Projects",
  summary: "Summary", certifications: "Certifications", achievements: "Achievements", responsibilities: "Responsibilities",
};
const err = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

function ResumeTool() {
  const [info, setInfo] = useState<ResumeInfo | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jd, setJd] = useState({ title: "", company: "", description: "" });
  const [match, setMatch] = useState<ATSMatch | null>(null);
  const [role, setRole] = useState("");
  const [review, setReview] = useState<ResumeReview | null>(null);

  useEffect(() => {
    api<ResumeInfo>("/resume").then(setInfo).catch((e) => setInfo(e instanceof ApiError && e.status === 404 ? null : undefined));
  }, []);

  async function upload(file: File | undefined) {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) return setError("File is larger than 2 MB.");
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      setInfo(await api<ResumeInfo>("/resume", { method: "POST", body: form }));
      setMatch(null);
      setReview(null);
    } catch (e) {
      setError(err(e, "Upload failed"));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm("Delete your resume from this app?")) return;
    await api("/resume", { method: "DELETE" }).catch(() => undefined);
    setInfo(null);
  }

  async function runMatch(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setMatch(await api<ATSMatch>("/resume/match", { method: "POST", body: JSON.stringify({
        job_title: jd.title, company: jd.company || null, description: jd.description }) }));
    } catch (e2) {
      setError(err(e2, "Match failed"));
    }
  }

  async function runReview(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const qs = role.trim() ? `?role=${encodeURIComponent(role.trim())}` : "";
      setReview(await api<ResumeReview>(`/resume/review${qs}`));
    } catch (e2) {
      setError(err(e2, "Review failed"));
    }
  }

  const input = "mt-1 w-full rounded border border-slate-300 px-3 py-2";
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h1 className="text-xl font-semibold">Your resume</h1>
        <p className="text-sm text-slate-600">
          PDF or DOCX, max 2 MB. The file itself isn&apos;t stored: we keep the extracted text with your email and phone
          number removed, plus the parsed skills. You can delete it any time.
        </p>
        <label className="mt-4 inline-block cursor-pointer rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
          {busy ? "Reading…" : info ? "Replace resume" : "Upload resume"}
          <input type="file" accept=".pdf,.docx" className="hidden" disabled={busy}
            onChange={(e) => upload(e.target.files?.[0])} />
        </label>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {info && (
          <div className="mt-5 space-y-3 text-sm">
            <p className="text-slate-600">
              {info.filename} · {info.kind.toUpperCase()}{info.pages ? ` · ${info.pages} page(s)` : ""} · {info.word_count} words
              <button onClick={remove} className="ml-3 text-red-600 hover:underline">Delete</button>
            </p>
            <div>
              <p className="mb-1 text-xs font-medium text-slate-600">Skills detected ({info.skills.length})</p>
              <div className="flex flex-wrap gap-1">
                {info.skills.map((s) => <span key={s} className="rounded bg-slate-100 px-2 py-0.5 text-xs">{s}</span>)}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(info.sections).map(([k, ok]) => (
                <span key={k} className={`rounded px-2 py-0.5 text-xs ${ok ? "bg-green-50 text-green-800" : "bg-slate-50 text-slate-400"}`}>
                  {ok ? "✓" : "–"} {SECTION_LABELS[k] ?? k}
                </span>
              ))}
            </div>
            {info.warnings.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-amber-800">{info.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            )}
          </div>
        )}
      </section>

      {info && (
        <>
          <section className="space-y-3">
            <form onSubmit={runReview} className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-4">
              <label className="flex-1 text-sm">Compare my skills with the market for this role
                <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. data analyst (default: your target role)"
                  className={input} />
              </label>
              <button className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">Review</button>
            </form>
            {review && <ReviewCard r={review} />}
          </section>

          <section className="space-y-3">
            <form onSubmit={runMatch} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2">
              <h2 className="font-semibold sm:col-span-2">Check against a specific job</h2>
              <label className="text-sm">Job title
                <input required minLength={2} value={jd.title} onChange={(e) => setJd({ ...jd, title: e.target.value })} className={input} />
              </label>
              <label className="text-sm">Company (optional)
                <input value={jd.company} onChange={(e) => setJd({ ...jd, company: e.target.value })} className={input} />
              </label>
              <label className="text-sm sm:col-span-2">Paste the full job description
                <textarea required minLength={50} rows={6} value={jd.description}
                  onChange={(e) => setJd({ ...jd, description: e.target.value })} className={input} />
              </label>
              <button className="rounded bg-blue-600 py-2 text-sm text-white hover:bg-blue-700 sm:col-span-2">Get ATS score</button>
              <p className="text-xs text-slate-500 sm:col-span-2">
                Tip: in the chat you can also ask “how does my resume match the first job?” after a search.
              </p>
            </form>
            {match && <ATSCard m={match} />}
          </section>
        </>
      )}
    </div>
  );
}

export default function ResumePage() {
  return <RequireAuth><ResumeTool /></RequireAuth>;
}
