"use client";
import { useEffect, useState } from "react";
import JobCard from "@/components/JobCard";
import RequireAuth from "@/components/RequireAuth";
import { Alert, AlertPreview, AlertRun, api, ApiError, describeSearch } from "@/lib/api";

function AlertRow({ a, onChange }: { a: Alert; onChange: () => void }) {
  const [preview, setPreview] = useState<AlertPreview | null>(null);
  const [runs, setRuns] = useState<AlertRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChange();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function runPreview() {
    setBusy(true);
    setError(null);
    try {
      setPreview(await api<AlertPreview>(`/alerts/${a.id}/preview`, { method: "POST" }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Preview failed");
    } finally {
      setBusy(false);
    }
  }

  async function loadRuns() {
    if (runs) return setRuns(null);
    try {
      setRuns(await api<AlertRun[]>(`/alerts/${a.id}/runs`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load history");
    }
  }

  const patch = (body: object) => act(() => api(`/alerts/${a.id}`, { method: "PATCH", body: JSON.stringify(body) }));

  return (
    <div className={`rounded-lg border border-slate-200 bg-white p-4 ${a.active ? "" : "opacity-60"}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-semibold">{a.name}</h3>
          <p className="text-xs text-slate-500">
            {describeSearch(a.params)} · {a.last_run_at ? `last run ${new Date(a.last_run_at).toLocaleString()}` : "not run yet"}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <select value={a.frequency} disabled={busy} onChange={(e) => patch({ frequency: e.target.value })}
            className="rounded border border-slate-300 px-2 py-1">
            <option value="daily">Daily</option><option value="weekly">Weekly</option>
          </select>
          <button disabled={busy} onClick={() => patch({ active: !a.active })}
            className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">{a.active ? "Pause" : "Resume"}</button>
          <button disabled={busy} onClick={runPreview}
            className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">Preview</button>
          <button disabled={busy} onClick={loadRuns}
            className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">{runs ? "Hide history" : "History"}</button>
          <button disabled={busy} onClick={() => confirm("Delete this alert?") && act(() => api(`/alerts/${a.id}`, { method: "DELETE" }))}
            className="px-2 py-1 text-red-600 hover:underline">Delete</button>
        </div>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {runs && (
        <div className="mt-3 space-y-2 text-sm">
          {runs.length === 0 && <p className="text-slate-500">No scheduled runs yet. Alerts run hourly when due.</p>}
          {runs.map((r) => (
            <div key={r.id} className="rounded bg-slate-50 p-2">
              <p className="text-xs text-slate-500">
                {new Date(r.ran_at).toLocaleString()} · {r.new_jobs} new · {r.emailed ? "emailed" : "in-app only"}
                {r.error && <span className="text-red-600"> · {r.error}</span>}
              </p>
              <ul className="list-disc pl-5">
                {r.digest.slice(0, 5).map((j) => (
                  <li key={j.id}>{/^https?:\/\//.test(j.url)
                    ? <a href={j.url} target="_blank" rel="noopener noreferrer" className="text-blue-700">{j.title}</a>
                    : j.title} · {j.company}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
      {preview && (
        <div className="mt-3 space-y-2">
          <p className="text-sm text-slate-600">
            {preview.new} new of {preview.total} matching job{preview.total === 1 ? "" : "s"} would be sent next time.
          </p>
          {preview.jobs.slice(0, 5).map((j) => <JobCard key={j.id} job={j} />)}
        </div>
      )}
    </div>
  );
}

function AlertList() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => api<Alert[]>("/alerts").then(setAlerts).catch((e) =>
    setError(e instanceof ApiError ? e.message : "Couldn't load alerts"));

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Job alerts</h1>
        <p className="text-sm text-slate-600">
          Saved searches that are re-run on a schedule; only jobs you haven&apos;t been sent before count as new.
          Create one from any search result. New jobs are emailed when due (or kept under History if email is off).
        </p>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {alerts?.length === 0 && <p className="text-sm text-slate-500">No alerts yet. Run a search and click “Save as alert”.</p>}
      {alerts?.map((a) => <AlertRow key={a.id} a={a} onChange={load} />)}
    </div>
  );
}

export default function AlertsPage() {
  return <RequireAuth><AlertList /></RequireAuth>;
}
