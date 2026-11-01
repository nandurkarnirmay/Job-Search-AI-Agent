"use client";
import { FormEvent, useEffect, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import { api, ApiError, Application, APP_STATUSES, AppStatus } from "@/lib/api";

const LABEL: Record<AppStatus, string> = { saved: "Saved", applied: "Applied", interview: "Interview", offer: "Offer",
  rejected: "Rejected", withdrawn: "Withdrawn" };
const ACTIVE: AppStatus[] = ["saved", "applied", "interview", "offer"];

function Card({ a, onChange }: { a: Application; onChange: () => void }) {
  const [notes, setNotes] = useState(a.notes ?? "");
  const patch = (body: object) =>
    api(`/applications/${a.id}`, { method: "PATCH", body: JSON.stringify(body) }).then(onChange).catch(() => undefined);
  const salary = a.salary_max_lpa ? ` · ₹${a.salary_min_lpa ?? a.salary_max_lpa}–${a.salary_max_lpa} LPA` : "";
  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <div>
        {a.url ? <a href={a.url} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-700">{a.title}</a>
          : <span className="font-medium">{a.title}</span>}
        <p className="text-xs text-slate-600">{a.company}{a.location ? ` · ${a.location}` : ""}{salary}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select value={a.status} onChange={(e) => patch({ status: e.target.value })}
          className="rounded border border-slate-300 px-1 py-0.5 text-xs">
          {APP_STATUSES.map((s) => <option key={s} value={s}>{LABEL[s]}</option>)}
        </select>
        <input type="date" value={a.next_action_on ?? ""} title="Next step (follow-up, interview date)"
          onChange={(e) => patch({ next_action_on: e.target.value || null })}
          className="rounded border border-slate-300 px-1 py-0.5 text-xs" />
        <button onClick={() => confirm("Remove from tracker?") &&
          api(`/applications/${a.id}`, { method: "DELETE" }).then(onChange)} className="text-xs text-red-600">Remove</button>
      </div>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} onBlur={() => notes !== (a.notes ?? "") && patch({ notes })}
        placeholder="Notes (referral, recruiter name…)" rows={2} maxLength={2000}
        className="w-full rounded border border-slate-200 px-2 py-1 text-xs" />
    </div>
  );
}

function Tracker() {
  const [apps, setApps] = useState<Application[]>([]);
  const [form, setForm] = useState({ title: "", company: "", url: "" });
  const [error, setError] = useState<string | null>(null);
  const load = () => api<Application[]>("/applications").then(setApps).catch(() => setApps([]));
  useEffect(() => { load(); }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/applications", { method: "POST", body: JSON.stringify({ title: form.title, company: form.company,
        url: form.url || null }) });
      setForm({ title: "", company: "", url: "" });
      load();
    } catch (e2) {
      setError(e2 instanceof ApiError ? e2.message : "Couldn't add");
    }
  }

  const closed = apps.filter((a) => !ACTIVE.includes(a.status));
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Application tracker</h1>
        <p className="text-sm text-slate-600">Save jobs from search results or the chat, then move them along as you apply.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {ACTIVE.map((s) => {
          const col = apps.filter((a) => a.status === s);
          return (
            <div key={s} className="space-y-2 rounded-lg bg-slate-100 p-3">
              <h2 className="text-sm font-semibold">{LABEL[s]} <span className="text-slate-500">({col.length})</span></h2>
              {col.map((a) => <Card key={a.id} a={a} onChange={load} />)}
            </div>
          );
        })}
      </div>
      {closed.length > 0 && (
        <details className="rounded-lg bg-slate-100 p-3">
          <summary className="cursor-pointer text-sm font-semibold">Closed ({closed.length})</summary>
          <div className="mt-2 grid gap-2 md:grid-cols-3">{closed.map((a) => <Card key={a.id} a={a} onChange={load} />)}</div>
        </details>
      )}
      <form onSubmit={add} className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <span className="w-full font-medium">Add a job you found elsewhere (LinkedIn, Naukri, referral…)</span>
        <input required minLength={2} placeholder="Job title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
          className="flex-1 rounded border border-slate-300 px-3 py-2" />
        <input required placeholder="Company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })}
          className="flex-1 rounded border border-slate-300 px-3 py-2" />
        <input type="url" placeholder="https://… (optional)" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })}
          className="flex-1 rounded border border-slate-300 px-3 py-2" />
        <button className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">Add</button>
        {error && <p className="w-full text-red-600">{error}</p>}
      </form>
    </div>
  );
}

export default function ApplicationsPage() {
  return <RequireAuth><Tracker /></RequireAuth>;
}
