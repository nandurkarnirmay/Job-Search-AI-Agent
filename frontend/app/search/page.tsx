"use client";
import { FormEvent, useState } from "react";
import Chat from "@/components/Chat";
import JobCard from "@/components/JobCard";
import RequireAuth from "@/components/RequireAuth";
import { api, ApiError, createAlert, Job, SearchResponse } from "@/lib/api";

const CITIES = ["", "Bengaluru", "Mumbai", "Delhi", "Gurugram", "Noida", "Hyderabad", "Chennai", "Pune", "Kolkata",
  "Ahmedabad", "Jaipur", "Kochi", "Bhubaneswar"];
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

function FilterSearch() {
  const [f, setF] = useState({ q: "", city: "", max_experience_years: "", min_salary_lpa: "", work_mode: "",
    notice_period_days: "" });
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [alertMsg, setAlertMsg] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setAlertMsg(null);
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v !== ""));
    try {
      setResult(await api<SearchResponse>(`/jobs/search?${qs}`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function saveAlert() {
    if (!result) return;
    try {
      await createAlert(result.params);
      setAlertMsg("Daily alert created. Manage it under Alerts.");
    } catch (err) {
      setAlertMsg(err instanceof ApiError ? err.message : "Couldn't create alert");
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
      {result && result.count > 0 && (
        <div className="mt-4 flex items-center gap-3">
          <button onClick={saveAlert} className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-white">
            🔔 Save as alert
          </button>
          {alertMsg && <span className="text-sm text-slate-600">{alertMsg}</span>}
        </div>
      )}
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
      {mode === "chat" ? <Chat /> : <FilterSearch />}
    </RequireAuth>
  );
}
