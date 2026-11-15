/**
 * Small, dependency-free charts. Single series each (one hue, so no legend or palette juggling), thin bars with
 * rounded data-ends on a shared baseline, a hover tooltip on every bar, selective labels (latest value), and
 * every chart has a table view for screen readers and anyone who prefers numbers.
 */
export function WeeklyBars({ title, values, weekStarts }: { title: string; values: number[]; weekStarts: string[] }) {
  const max = Math.max(...values, 1);
  const total = values.reduce((a, b) => a + b, 0);
  return (
    <figure className="rounded-lg border border-slate-200 bg-white p-3">
      <figcaption className="flex items-baseline justify-between text-sm">
        <span className="font-medium">{title}</span>
        <span className="text-xs text-slate-500">{total} in 8 weeks</span>
      </figcaption>
      <div className="mt-3 flex h-20 items-end gap-1" aria-hidden>
        {values.map((v, i) => (
          <div key={i} className="group relative flex h-full flex-1 items-end">
            <div className="w-full rounded-t bg-blue-600 transition-opacity group-hover:opacity-80"
              style={{ height: `${v ? Math.max((v / max) * 100, 4) : 0}%` }} />
            <span className="pointer-events-none absolute -top-6 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-800 px-1.5 py-0.5 text-xs text-white group-hover:block">
              week of {weekStarts[i]}: {v}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-1 h-px bg-slate-300" />
      <div className="mt-1 flex justify-between text-[10px] text-slate-500"><span>8 wks ago</span><span>this week: {values[values.length - 1]}</span></div>
      <details className="mt-1 text-xs text-slate-600">
        <summary className="cursor-pointer">Table</summary>
        <table className="mt-1 w-full">
          <tbody>{values.map((v, i) => <tr key={i}><td>{weekStarts[i]}</td><td className="text-right">{v}</td></tr>)}</tbody>
        </table>
      </details>
    </figure>
  );
}

export function HBars({ rows, unit = "", caption }: { rows: { label: string; value: number; note?: string }[]; unit?: string; caption: string }) {
  const max = Math.max(...rows.map((r) => r.value), 1);
  return (
    <table className="w-full text-sm" aria-label={caption}>
      <tbody>
        {rows.map((r) => (
          <tr key={r.label} title={`${r.label}: ${r.value}${unit}${r.note ? ` (${r.note})` : ""}`}>
            <td className="w-28 py-1 pr-2 text-slate-600">{r.label}</td>
            <td className="py-1">
              <div className="h-3 rounded-r bg-blue-600" style={{ width: `${r.value ? Math.max((r.value / max) * 100, 2) : 0}%` }} />
            </td>
            <td className="w-24 py-1 pl-2 text-right tabular-nums">{r.value}{unit}{r.note ? <span className="text-xs text-slate-500"> {r.note}</span> : null}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
