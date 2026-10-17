"use client";
import { FormEvent, useState } from "react";
import JobCard from "@/components/JobCard";
import RequireAuth from "@/components/RequireAuth";
import { api, ApiError, ChatResponse, Job, SearchResponse } from "@/lib/api";

const CITIES = ["", "Bengaluru", "Mumbai", "Delhi", "Gurugram", "Noida", "Hyderabad", "Chennai", "Pune", "Kolkata",
  "Ahmedabad", "Jaipur", "Kochi", "Bhubaneswar"];
const EXAMPLES = [
  "Remote Python developer jobs in Bengaluru above 8 LPA",
  "Fresher data analyst openings in Pune",
  "React developer, 3 years experience, hybrid, Gurugram, 60 days notice",
];

type Mode = "chat" | "filters";

function Results({ jobs, meta }: { jobs: Job[]; meta?: string }) {
  if (!jobs.length) return null;
  return (
    <div className="mt-6 space-y-3">
      {meta && <p className="text-xs text-slate-500">{meta}</p>}
      {jobs.map((j) => <JobCard key={j.id} job={j} />)}
    </div>
  );
}

function ChatSearch() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(text: string) {
    if (text.trim().length < 2) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ message: text }) }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <form onSubmit={(e: FormEvent) => { e.preventDefault(); send(message); }} className="flex gap-2">
        <input value={message} onChange={(e) => setMessage(e.target.value)} maxLength={500}
          placeholder="Describe the job you want…" className="flex-1 rounded border border-slate-300 px-3 py-2" />
        <button disabled={busy} className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50">
          {busy ? "Searching…" : "Ask"}
        </button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => { setMessage(ex); send(ex); }}
            className="rounded-full border border-slate-300 px-3 py-1 text-xs hover:bg-white">{ex}</button>
        ))}
      </div>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {result && (
        <div className="mt-6 whitespace-pre-line rounded-lg bg-blue-50 p-4 text-sm">{result.reply}</div>
      )}
      {result && <Results jobs={result.jobs} meta={`Understood by: ${result.parser === "llm" ? "Gemini" : "rule parser"}`} />}
    </div>
  );
}

function FilterSearch() {
  const [f, setF] = useState({ q: "", city: "", max_experience_years: "", min_salary_lpa: "", work_mode: "",
    notice_period_days: "" });
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v !== ""));
    try {
      setResult(await api<SearchResponse>(`/jobs/search?${qs}`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const input = "mt-1 w-full rounded border border-slate-300 px-3 py-2";
  return (
    <div>
      <form onSubmit={submit} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-3">
        <label className="text-sm sm:col-span-3">Role or skills
          <input required minLength={2} value={f.q} onChange={set("q")} placeholder="e.g. java backend" className={input} />
        </label>
        <label className="text-sm">City
          <select value={f.city} onChange={set("city")} className={input}>
            {CITIES.map((c) => <option key={c} value={c}>{c || "Anywhere in India"}</option>)}
          </select>
        </label>
        <label className="text-sm">Your experience (years)
          <input type="number" min={0} max={50} step={0.5} value={f.max_experience_years}
            onChange={set("max_experience_years")} className={input} />
        </label>
        <label className="text-sm">Minimum salary (LPA)
          <input type="number" min={0} max={500} step={0.5} value={f.min_salary_lpa} onChange={set("min_salary_lpa")}
            className={input} />
        </label>
        <label className="text-sm">Work mode
          <select value={f.work_mode} onChange={set("work_mode")} className={input}>
            <option value="">Any</option><option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option><option value="onsite">On-site</option>
          </select>
        </label>
        <label className="text-sm">Your notice period
          <select value={f.notice_period_days} onChange={set("notice_period_days")} className={input}>
            <option value="">Any</option><option value="0">Immediate</option><option value="30">30 days</option>
            <option value="60">60 days</option><option value="90">90 days</option>
          </select>
        </label>
        <div className="flex items-end">
          <button disabled={busy} className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50">
            {busy ? "Searching…" : "Search"}
          </button>
        </div>
      </form>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {result && result.count === 0 && <p className="mt-6 text-slate-600">No jobs match. Loosen a filter.</p>}
      {result && (
        <Results jobs={result.jobs} meta={`${result.count} jobs · ${result.latency_ms} ms${result.cache_hit ? " (cached)" : ""}` +
          (result.sources_failed.length ? ` · unavailable: ${result.sources_failed.join(", ")}` : "")} />
      )}
    </div>
  );
}

export default function SearchPage() {
  const [mode, setMode] = useState<Mode>("chat");
  const tab = (m: Mode) => `rounded px-4 py-1.5 text-sm ${mode === m ? "bg-white shadow" : "text-slate-600"}`;
  return (
    <RequireAuth>
      <div className="mb-6 inline-flex rounded-lg bg-slate-200 p-1">
        <button className={tab("chat")} onClick={() => setMode("chat")}>Ask the agent</button>
        <button className={tab("filters")} onClick={() => setMode("filters")}>Filters</button>
      </div>
      {mode === "chat" ? <ChatSearch /> : <FilterSearch />}
    </RequireAuth>
  );
}
