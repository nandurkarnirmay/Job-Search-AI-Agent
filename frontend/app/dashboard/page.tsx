"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { HBars, StatTile, WeeklyBars } from "@/components/Charts";
import RequireAuth from "@/components/RequireAuth";
import { api, ApiError, CalendarEvent, MyAnalytics, safeUrl } from "@/lib/api";

const pct = (x: number | null) => (x == null ? "–" : `${Math.round(x * 100)}%`);
const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short",
  hour: "numeric", minute: "2-digit" });

function Dashboard() {
  const [m, setM] = useState<MyAnalytics | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<MyAnalytics>("/analytics/me").then(setM).catch((e) => setError(e instanceof ApiError ? e.message : "Couldn't load"));
    api<CalendarEvent[]>("/calendar/events").then((ev) => setEvents(ev.filter((e) => new Date(e.starts_at) > new Date()).slice(0, 5)))
      .catch(() => setEvents([]));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!m) return <p className="text-slate-500">Loading…</p>;
  const f = m.funnel;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h1 className="text-xl font-semibold">Your job search</h1>
        <div className="flex flex-wrap gap-2 text-sm">
          <Link href="/search" className="rounded bg-blue-600 px-3 py-1.5 text-white hover:bg-blue-700">Ask the agent</Link>
          <Link href="/career" className="rounded border border-slate-300 px-3 py-1.5 hover:bg-white">Career tools</Link>
          <Link href="/interview" className="rounded border border-slate-300 px-3 py-1.5 hover:bg-white">Practise</Link>
        </div>
      </div>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Tracked jobs" value={String(f.tracked)} hint={`${f.applied} applied`} />
        <StatTile label="Interview rate" value={pct(f.interview_rate)} hint={`${f.interviews} of ${f.applied} applications`} />
        <StatTile label="Offer rate" value={pct(f.offer_rate)} hint={`${f.offers} of ${f.interviews} interviews`} />
        <StatTile label="Saved → applied" value={f.median_days_saved_to_applied == null ? "–" : `${f.median_days_saved_to_applied} d`} hint="median days" />
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <WeeklyBars title="Searches" values={m.weekly.searches} weekStarts={m.week_starts} />
        <WeeklyBars title="Jobs saved" values={m.weekly.applications} weekStarts={m.week_starts} />
        <WeeklyBars title="Practice sessions" values={m.weekly.practice_sessions} weekStarts={m.week_starts} />
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-2 font-semibold">Funnel</h2>
          <HBars caption="Applications by furthest stage reached" rows={[
            { label: "Tracked", value: f.tracked }, { label: "Applied", value: f.applied },
            { label: "Interview", value: f.interviews }, { label: "Offer", value: f.offers }]} />
          <p className="mt-2 text-xs text-slate-500">Counts what each application ever reached, so a rejection after an interview still counts as an interview.</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-2 font-semibold">Interview practice</h2>
          {m.practice_trend.length ? (
            <HBars caption="Average answer score per practice session (out of 5)" unit="/5" rows={m.practice_trend.map((p) => ({
              label: `#${p.session} ${p.role.slice(0, 14)}`, value: p.average, note: `${p.answered} ans.` }))} />
          ) : <p className="text-sm text-slate-500">No answered practice questions yet.</p>}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-2 font-semibold">Upcoming</h2>
          {events.length ? (
            <ul className="space-y-2 text-sm">
              {events.map((e) => (
                <li key={e.id} className="flex justify-between gap-2">
                  <span><b>{when(e.starts_at)}</b> · {e.title}</span>
                  <a href={safeUrl(e.google_calendar_url)} target="_blank" rel="noopener noreferrer" className="shrink-0 text-xs text-blue-700">Google Calendar ↗</a>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-slate-500">Nothing scheduled. Add interviews on the <Link href="/applications" className="text-blue-700">Tracker</Link>.</p>}
        </div>
        <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <h2 className="font-semibold">Activity</h2>
          <p>Top searches: {m.top_searches.length ? m.top_searches.map((s) => `${s.keywords} (${s.count})`).join(", ") : "–"}</p>
          <p>Alerts: {m.alerts.active} active · {m.alerts.runs} runs · {m.alerts.new_jobs_found} new jobs found</p>
          <p>Roadmap skills: {Object.keys(m.skills).length ? Object.entries(m.skills).map(([k, v]) => `${v} ${k}`).join(", ") : "none tracked yet"}</p>
        </div>
      </section>
    </div>
  );
}

export default function DashboardPage() {
  return <RequireAuth><Dashboard /></RequireAuth>;
}
