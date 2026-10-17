import type { Job } from "@/lib/api";

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

export default function JobCard({ job }: { job: Job }) {
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
        <a href={job.url} target="_blank" rel="noopener noreferrer"
          className="shrink-0 rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700">Apply</a>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {tags.map((t) => <span key={t} className="rounded bg-slate-100 px-2 py-0.5 text-xs">{t}</span>)}
        <span className="rounded bg-slate-50 px-2 py-0.5 text-xs text-slate-400">via {job.source}</span>
      </div>
    </article>
  );
}
