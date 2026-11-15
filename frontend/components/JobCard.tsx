"use client";
import { useState } from "react";
import { ApiError, saveJob, type Job } from "@/lib/api";

function SaveButton({ jobId }: { jobId: string }) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [msg, setMsg] = useState("");
  async function save() {
    setState("saving");
    try {
      await saveJob(jobId);
      setState("saved");
    } catch (e) {
      // already tracked counts as saved
      if (e instanceof ApiError && e.code === "already_tracked") return setState("saved");
      setMsg(e instanceof ApiError ? e.message : "Couldn't save");
      setState("error");
    }
  }
  if (state === "saved") return <span className="shrink-0 rounded border border-green-300 px-3 py-1 text-sm text-green-700">Saved ✓</span>;
  return (
    <button onClick={save} disabled={state === "saving"} title={msg || "Add to your application tracker"}
      className="shrink-0 rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-50 disabled:opacity-50">
      {state === "error" ? "Retry save" : "Save"}
    </button>
  );
}

function salary(j: Job): string {
  const lo = j.salary_min_lpa ?? j.salary_max_lpa;
  const hi = j.salary_max_lpa ?? j.salary_min_lpa;
  if (lo == null || hi == null) return "Salary not disclosed";
  return lo === hi ? `₹${lo} LPA` : `₹${lo}–${hi} LPA`;
}

function experience(j: Job): string | null {
  if (j.experience_min_years == null) return null;
  if (j.experience_min_years === 0) return "Fresher";
  return j.experience_max_years != null
    ? `${j.experience_min_years}–${j.experience_max_years} yrs`
    : `${j.experience_min_years}+ yrs`;
}

export default function JobCard({ job, canSave = true }: { job: Job; canSave?: boolean }) {
  const tags = [
    salary(job),
    experience(job),
    job.work_mode && job.work_mode[0].toUpperCase() + job.work_mode.slice(1),
    job.notice_period_days === 0 ? "Immediate joiner" : job.notice_period_days != null ? `≤${job.notice_period_days}d notice` : null,
  ].filter(Boolean) as string[];

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold">{job.title}</h3>
          <p className="text-sm text-slate-600">{job.company} · {job.location}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          {canSave && <SaveButton jobId={job.id} />}
          {/^https?:\/\//.test(job.url) && (
            <a href={job.url} target="_blank" rel="noopener noreferrer"
              className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">Apply</a>
          )}
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {tags.map((t) => <span key={t} className="rounded bg-slate-100 px-2 py-0.5 text-xs">{t}</span>)}
        <span className="rounded bg-slate-50 px-2 py-0.5 text-xs text-slate-400">via {job.source}</span>
      </div>
    </article>
  );
}
