import type { CompanyReport, SalaryReport, SalaryStats } from "@/lib/api";

function Stats({ label, s, note }: { label: string; s: SalaryStats; note?: string }) {
  // bar shows the middle half (p25–p75) inside the full range, median marked
  const span = Math.max(s.max - s.min, 0.1);
  const pos = (x: number) => `${((x - s.min) / span) * 100}%`;
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-xs text-slate-500">n = {s.n}{note ? ` · ${note}` : ""}</span>
      </div>
      <div className="relative h-2 rounded bg-slate-100">
        <div className="absolute h-2 rounded bg-blue-300" style={{ left: pos(s.p25), width: `calc(${pos(s.p75)} - ${pos(s.p25)})` }} />
        <div className="absolute -top-1 h-4 w-0.5 bg-blue-700" style={{ left: pos(s.median) }} />
      </div>
      <div className="flex justify-between text-xs text-slate-600">
        <span>₹{s.min}L</span>
        <span>median <b>₹{s.median} LPA</b> · middle half ₹{s.p25}–{s.p75}L</span>
        <span>₹{s.max}L</span>
      </div>
    </div>
  );
}

export function SalaryCard({ r }: { r: SalaryReport }) {
  const where = r.city ?? "India";
  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="font-semibold">Salary: {r.role}, {where}</h3>
      {r.listings && <Stats label="Advertised in current listings" s={r.listings} />}
      {r.market && <Stats label="Market estimate (Adzuna)" s={r.market} note="includes estimates" />}
      {!r.listings && !r.market && <p className="text-sm text-slate-600">Not enough data for a reliable range.</p>}
      {r.notes.map((n) => <p key={n} className="text-xs text-slate-500">{n}</p>)}
    </div>
  );
}

export function CompanyCard({ r }: { r: CompanyReport }) {
  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div>
        <h3 className="font-semibold">{r.name}</h3>
        {r.wiki?.description && <p className="text-sm text-slate-600">{r.wiki.description}</p>}
      </div>
      {r.wiki && (
        <p className="text-sm">
          {r.wiki.extract}{" "}
          {r.wiki.url && <a href={r.wiki.url} target="_blank" rel="noopener noreferrer" className="text-blue-700">Wikipedia</a>}
        </p>
      )}
      {r.open_roles != null && (
        <div className="text-sm">
          <p className="font-medium">
            {r.open_roles} opening{r.open_roles === 1 ? "" : "s"} in our sources
            {r.top_cities.length > 0 && <span className="font-normal text-slate-600"> · {r.top_cities.join(", ")}</span>}
          </p>
          <ul className="mt-1 list-disc pl-5">
            {r.sample_roles.map((j) => (
              <li key={j.url + j.title}>
                <a href={j.url} target="_blank" rel="noopener noreferrer" className="text-blue-700">{j.title}</a> · {j.location}
              </li>
            ))}
          </ul>
        </div>
      )}
      {r.disclosed_salary && <Stats label="Disclosed salaries in these openings" s={r.disclosed_salary} />}
      {r.notes.map((n) => <p key={n} className="text-xs text-slate-500">{n}</p>)}
    </div>
  );
}
