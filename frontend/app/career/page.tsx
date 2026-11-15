"use client";
import { FormEvent, useEffect, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import { SalaryCard } from "@/components/Reports";
import { CareerCard, GitHubCard, NegotiationCard } from "@/components/Week5Cards";
import { api, ApiError, CareerPath, GitHubReport, NegotiationAdvice, Profile, RoadmapStep, SalaryReport } from "@/lib/api";

type Tab = "roadmap" | "salary" | "negotiate" | "github";
const TABS: [Tab, string][] = [["roadmap", "Career roadmap"], ["salary", "Salary benchmark"], ["negotiate", "Negotiate an offer"],
  ["github", "GitHub review"]];
const input = "mt-1 w-full rounded border border-slate-300 px-3 py-2";
const errText = (e: unknown, f: string) => (e instanceof ApiError ? e.message : f);
const num = (s: string) => (s.trim() === "" ? null : Number(s));

function Roadmap({ defaultRole }: { defaultRole: string }) {
  const [role, setRole] = useState(defaultRole);
  const [path, setPath] = useState<CareerPath | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(e?: FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setPath(await api<CareerPath>(`/career/path${role.trim() ? `?role=${encodeURIComponent(role.trim())}` : ""}`));
    } catch (err) {
      setError(errText(err, "Couldn't build the roadmap"));
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(skill: string, status: RoadmapStep["status"]) {
    try {
      await api("/career/progress", { method: "PUT", body: JSON.stringify({ skill, status }) });
      await load();
    } catch (err) {
      setError(errText(err, "Couldn't save progress"));
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={load} className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <label className="flex-1 text-sm">Target role
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. data engineer (default: your profile's target role)" className={input} />
        </label>
        <button disabled={busy} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
          {busy ? "Building…" : "Build roadmap"}</button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {path && <CareerCard p={path} onStatus={setStatus} />}
      {path && <p className="text-xs text-slate-500">Click a skill&apos;s status to cycle To do → Learning → Done. Done skills leave the plan.</p>}
    </div>
  );
}

function Salary() {
  const [f, setF] = useState({ role: "", city: "", exp: "" });
  const [r, setR] = useState<SalaryReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function go(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const qs = new URLSearchParams({ role: f.role, ...(f.city ? { city: f.city } : {}), ...(f.exp ? { experience_years: f.exp } : {}) });
    try {
      setR(await api<SalaryReport>(`/salary/benchmark?${qs}`));
    } catch (err) {
      setError(errText(err, "Benchmark failed"));
    }
  }
  return (
    <div className="space-y-4">
      <form onSubmit={go} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-4">
        <label className="text-sm sm:col-span-2">Role<input required minLength={2} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} className={input} /></label>
        <label className="text-sm">City<input value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })} className={input} /></label>
        <label className="text-sm">Experience (yrs)<input type="number" min={0} max={50} step={0.5} value={f.exp} onChange={(e) => setF({ ...f, exp: e.target.value })} className={input} /></label>
        <button className="rounded bg-blue-600 py-2 text-sm text-white hover:bg-blue-700 sm:col-span-4">Benchmark</button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {r && <SalaryCard r={r} />}
      {r?.bands && !r.bands.some((b) => b.stats) && <p className="text-sm text-slate-500">Not enough listings state both salary and experience for a per-band view.</p>}
    </div>
  );
}

function Negotiate({ defaultRole }: { defaultRole: string }) {
  const [f, setF] = useState({ role: defaultRole, offer: "", city: "", exp: "", current: "", competing: "", notice: "" });
  const [a, setA] = useState<NegotiationAdvice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  async function go(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setA(await api<NegotiationAdvice>("/salary/negotiate", { method: "POST", body: JSON.stringify({
        role: f.role, offer_lpa: Number(f.offer), city: f.city || null, experience_years: num(f.exp),
        current_lpa: num(f.current), competing_offer_lpa: num(f.competing), notice_period_days: num(f.notice) }) }));
    } catch (err) {
      setError(errText(err, "Couldn't evaluate the offer"));
    }
  }
  return (
    <div className="space-y-4">
      <form onSubmit={go} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-3">
        <label className="text-sm">Role<input required minLength={2} value={f.role} onChange={set("role")} className={input} /></label>
        <label className="text-sm">Offer (CTC, LPA)<input required type="number" min={0.5} max={500} step={0.1} value={f.offer} onChange={set("offer")} className={input} /></label>
        <label className="text-sm">City<input value={f.city} onChange={set("city")} className={input} /></label>
        <label className="text-sm">Your experience (yrs)<input type="number" min={0} max={50} step={0.5} value={f.exp} onChange={set("exp")} className={input} /></label>
        <label className="text-sm">Current CTC (LPA)<input type="number" min={0} max={500} step={0.1} value={f.current} onChange={set("current")} className={input} /></label>
        <label className="text-sm">Competing offer (LPA)<input type="number" min={0} max={500} step={0.1} value={f.competing} onChange={set("competing")} className={input} /></label>
        <label className="text-sm">Notice period (days)<input type="number" min={0} max={180} value={f.notice} onChange={set("notice")} className={input} /></label>
        <div className="flex items-end sm:col-span-2"><button className="w-full rounded bg-blue-600 py-2 text-sm text-white hover:bg-blue-700">Evaluate offer</button></div>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {a && <NegotiationCard a={a} />}
    </div>
  );
}

function GitHub({ defaultUser }: { defaultUser: string }) {
  const [u, setU] = useState(defaultUser);
  const [r, setR] = useState<GitHubReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  async function go(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      setR(await api<GitHubReport>("/github/analyse", { method: "POST", body: JSON.stringify({ username: u }) }));
    } catch (err) {
      setError(errText(err, "GitHub analysis failed"));
    }
  }
  return (
    <div className="space-y-4">
      <form onSubmit={go} className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <label className="flex-1 text-sm">GitHub username<input required value={u} onChange={(e) => setU(e.target.value)} placeholder="e.g. asha-dev" className={input} /></label>
        <button className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">Analyse</button>
      </form>
      <p className="text-xs text-slate-500">Only public GitHub data is read. Results are compared with your uploaded resume.</p>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {r && <GitHubCard r={r} />}
    </div>
  );
}

function CareerTools() {
  const [tab, setTab] = useState<Tab>("roadmap");
  const [profile, setProfile] = useState<Profile | null>(null);
  useEffect(() => { api<Profile>("/me/profile").then(setProfile).catch(() => setProfile(null)); }, []);
  const role = profile?.target_roles?.[0] ?? "";
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Career tools</h1>
      <div className="flex flex-wrap gap-1 rounded-lg bg-slate-200 p-1" role="tablist">
        {TABS.map(([t, label]) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`rounded px-3 py-1.5 text-sm ${tab === t ? "bg-white shadow" : "text-slate-600"}`}>{label}</button>
        ))}
      </div>
      {tab === "roadmap" && <Roadmap key={role} defaultRole={role} />}
      {tab === "salary" && <Salary />}
      {tab === "negotiate" && <Negotiate key={role} defaultRole={role} />}
      {tab === "github" && <GitHub key={profile?.github_username ?? ""} defaultUser={profile?.github_username ?? ""} />}
    </div>
  );
}

export default function CareerPage() {
  return <RequireAuth><CareerTools /></RequireAuth>;
}
