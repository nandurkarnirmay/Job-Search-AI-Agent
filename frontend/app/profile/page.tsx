"use client";
import { FormEvent, useEffect, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import { api, ApiError, Profile } from "@/lib/api";

const list = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
const num = (s: string) => (s === "" ? null : Number(s));

function ProfileForm() {
  const [form, setForm] = useState({ full_name: "", current_city: "", preferred_cities: "", experience_years: "",
    skills: "", expected_lpa: "", notice_period_days: "", work_mode: "any", career_goal: "", target_roles: "",
    open_to_relocation: "" });
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    api<Profile>("/me/profile").then((p) => setForm({
      full_name: p.full_name ?? "", current_city: p.current_city ?? "",
      preferred_cities: p.preferred_cities.join(", "), experience_years: p.experience_years?.toString() ?? "",
      skills: p.skills.join(", "), expected_lpa: p.expected_lpa?.toString() ?? "",
      notice_period_days: p.notice_period_days?.toString() ?? "", work_mode: p.work_mode ?? "any",
      career_goal: p.career_goal ?? "", target_roles: p.target_roles.join(", "),
      open_to_relocation: p.open_to_relocation == null ? "" : p.open_to_relocation ? "yes" : "no",
    })).catch((e) => setStatus({ ok: false, text: e instanceof ApiError ? e.message : "Couldn't load profile" }));
  }, []);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  async function save(e: FormEvent) {
    e.preventDefault();
    setStatus(null);
    try {
      await api<Profile>("/me/profile", {
        method: "PUT",
        body: JSON.stringify({
          full_name: form.full_name || null, current_city: form.current_city || null,
          preferred_cities: list(form.preferred_cities), experience_years: num(form.experience_years),
          skills: list(form.skills), expected_lpa: num(form.expected_lpa),
          notice_period_days: num(form.notice_period_days), work_mode: form.work_mode,
          career_goal: form.career_goal.trim() || null, target_roles: list(form.target_roles),
          open_to_relocation: form.open_to_relocation === "" ? null : form.open_to_relocation === "yes",
        }),
      });
      setStatus({ ok: true, text: "Saved. The agent uses these as defaults; \"show me jobs\" searches your main target role." });
    } catch (err) {
      setStatus({ ok: false, text: err instanceof ApiError ? err.message : "Save failed" });
    }
  }

  const input = "mt-1 w-full rounded border border-slate-300 px-3 py-2";
  return (
    <form onSubmit={save} className="grid gap-4 rounded-lg border border-slate-200 bg-white p-6 sm:grid-cols-2">
      <h1 className="text-xl font-semibold sm:col-span-2">Your profile</h1>
      <label className="text-sm">Full name<input value={form.full_name} onChange={set("full_name")} className={input} /></label>
      <label className="text-sm">Current city<input value={form.current_city} onChange={set("current_city")} className={input} /></label>
      <label className="text-sm">Preferred cities (comma-separated)
        <input value={form.preferred_cities} onChange={set("preferred_cities")} placeholder="Bengaluru, Pune" className={input} />
      </label>
      <label className="text-sm">Experience (years)
        <input type="number" min={0} max={50} step={0.5} value={form.experience_years} onChange={set("experience_years")} className={input} />
      </label>
      <label className="text-sm sm:col-span-2">Target roles (comma-separated, first one is your main goal)
        <input value={form.target_roles} onChange={set("target_roles")} placeholder="Backend Developer, Data Engineer"
          className={input} />
      </label>
      <label className="text-sm sm:col-span-2">Career goal (max 500 characters)
        <textarea value={form.career_goal} onChange={set("career_goal")} maxLength={500} rows={2}
          placeholder="e.g. Backend engineer at a product company within 2 years" className={input} />
      </label>
      <label className="text-sm">Open to relocation
        <select value={form.open_to_relocation} onChange={set("open_to_relocation")} className={input}>
          <option value="">Not specified</option><option value="yes">Yes</option><option value="no">No</option>
        </select>
      </label>
      <label className="text-sm sm:col-span-2">Skills (comma-separated)
        <input value={form.skills} onChange={set("skills")} placeholder="python, sql, react" className={input} />
      </label>
      <label className="text-sm">Expected salary (LPA)
        <input type="number" min={0} max={500} step={0.5} value={form.expected_lpa} onChange={set("expected_lpa")} className={input} />
      </label>
      <label className="text-sm">Notice period (days)
        <input type="number" min={0} max={180} value={form.notice_period_days} onChange={set("notice_period_days")} className={input} />
      </label>
      <label className="text-sm">Preferred work mode
        <select value={form.work_mode} onChange={set("work_mode")} className={input}>
          <option value="any">Any</option><option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option><option value="onsite">On-site</option>
        </select>
      </label>
      <div className="flex items-end">
        <button className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700">Save profile</button>
      </div>
      {status && <p className={`text-sm sm:col-span-2 ${status.ok ? "text-green-700" : "text-red-600"}`}>{status.text}</p>}
    </form>
  );
}

export default function ProfilePage() {
  return <RequireAuth><ProfileForm /></RequireAuth>;
}
