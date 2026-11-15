"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, ApiError, Application, CalendarEvent, download, EventKind, safeUrl } from "@/lib/api";

const KINDS: [EventKind, string][] = [["interview", "Interview"], ["follow_up", "Follow-up"], ["deadline", "Deadline"], ["other", "Other"]];
const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short",
  hour: "numeric", minute: "2-digit" });

export default function CalendarPanel({ apps }: { apps: Application[] }) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [form, setForm] = useState({ kind: "interview" as EventKind, title: "", at: "", minutes: "60", location: "", app: "" });
  const [feed, setFeed] = useState<{ feed_url: string; webcal_url: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { api<CalendarEvent[]>("/calendar/events").then(setEvents).catch(() => setEvents([])); }, []);
  useEffect(load, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/calendar/events", { method: "POST", body: JSON.stringify({
        kind: form.kind, title: form.title, starts_at: new Date(form.at).toISOString(),  // local time → UTC with zone
        duration_minutes: Number(form.minutes), location: form.location || null,
        application_id: form.app ? Number(form.app) : null }) });
      setForm({ ...form, title: "", at: "", location: "" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add the event");
    }
  }

  async function subscribe(rotate = false) {
    if (rotate && !confirm("Create a new link? The old one stops working.")) return;
    try {
      setFeed(await api("/calendar/feed", { method: "POST" }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create the feed");
    }
  }

  const fieldCls = "rounded border border-slate-300 px-2 py-1.5 text-sm";
  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">Calendar</h2>
        <div className="flex gap-2 text-sm">
          <button onClick={() => subscribe(false)} className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">Subscribe in Google/Outlook</button>
          {feed && <button onClick={() => subscribe(true)} className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50">New link</button>}
        </div>
      </div>
      {feed && (
        <div className="rounded bg-slate-50 p-3 text-xs">
          <p>Google Calendar → Other calendars → <b>From URL</b>, paste this private link (it also includes your tracker&apos;s next-step dates):</p>
          <input readOnly value={feed.feed_url} onFocus={(e) => e.currentTarget.select()} className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1 font-mono" />
          <p className="mt-1 text-slate-500">Treat it like a password. Apple/Outlook: <a href={feed.webcal_url} className="text-blue-700">open as webcal</a>.</p>
        </div>
      )}
      <form onSubmit={add} className="grid gap-2 sm:grid-cols-6">
        <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as EventKind })} className={fieldCls}>
          {KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <input required minLength={2} placeholder="e.g. Interview: Data Analyst, Infosys" value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })} className={`${fieldCls} sm:col-span-2`} />
        <input required type="datetime-local" value={form.at} onChange={(e) => setForm({ ...form, at: e.target.value })} className={fieldCls} />
        <select value={form.minutes} onChange={(e) => setForm({ ...form, minutes: e.target.value })} className={fieldCls}>
          {[30, 45, 60, 90, 120, 180].map((m) => <option key={m} value={m}>{m} min</option>)}
        </select>
        <button className="rounded bg-blue-600 py-1.5 text-sm text-white hover:bg-blue-700">Add</button>
        <input placeholder="Meeting link or address (optional)" value={form.location}
          onChange={(e) => setForm({ ...form, location: e.target.value })} className={`${fieldCls} sm:col-span-3`} />
        <select value={form.app} onChange={(e) => setForm({ ...form, app: e.target.value })} className={`${fieldCls} sm:col-span-3`}>
          <option value="">Not linked to a tracked job</option>
          {apps.map((a) => <option key={a.id} value={a.id}>{a.title} · {a.company}</option>)}
        </select>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {events.length === 0 ? <p className="text-sm text-slate-500">No events yet. You get an email reminder the day before (when email is set up).</p> : (
        <ul className="divide-y divide-slate-100 text-sm">
          {events.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span><b>{when(e.starts_at)}</b> · {e.title}{e.location ? ` · ${e.location}` : ""}</span>
              <span className="flex gap-3 text-xs">
                <a href={safeUrl(e.google_calendar_url)} target="_blank" rel="noopener noreferrer" className="text-blue-700">Google ↗</a>
                <button onClick={() => download(`/calendar/events/${e.id}.ics`, `event-${e.id}.ics`)} className="text-blue-700">.ics</button>
                <button onClick={() => confirm("Delete this event?") && api(`/calendar/events/${e.id}`, { method: "DELETE" }).then(load)}
                  className="text-red-600">Delete</button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
