"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import { api, ApiError, InterviewSession } from "@/lib/api";

function Sessions() {
  const router = useRouter();
  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [form, setForm] = useState({ role: "", company: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<InterviewSession[]>("/interview/sessions").then(setSessions).catch(() => setSessions([]));
  }, []);

  async function start(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await api<InterviewSession>("/interview/sessions", {
        method: "POST", body: JSON.stringify({ role: form.role, company: form.company || null }),
      });
      router.push(`/interview/${s.id}`);
    } catch (e2) {
      setError(e2 instanceof ApiError ? e2.message : "Couldn't start");
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={start} className="grid gap-3 rounded-lg border border-slate-200 bg-white p-6 sm:grid-cols-3">
        <h1 className="text-xl font-semibold sm:col-span-3">Interview practice</h1>
        <p className="text-sm text-slate-600 sm:col-span-3">
          HR, technical and behavioural questions for the role, with feedback on each typed answer. In the chat you can
          also say “prepare me for the first job”.
        </p>
        <input required minLength={2} placeholder="Role, e.g. Data Analyst" value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })} className="rounded border border-slate-300 px-3 py-2" />
        <input placeholder="Company (optional)" value={form.company}
          onChange={(e) => setForm({ ...form, company: e.target.value })} className="rounded border border-slate-300 px-3 py-2" />
        <button disabled={busy} className="rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50">
          {busy ? "Preparing…" : "Start"}
        </button>
        {error && <p className="text-sm text-red-600 sm:col-span-3">{error}</p>}
      </form>
      {sessions.length > 0 && (
        <div className="space-y-2">
          <h2 className="font-semibold">Previous sessions</h2>
          {sessions.map((s) => {
            const answered = Object.keys(s.answers).length;
            return (
              <Link key={s.id} href={`/interview/${s.id}`}
                className="flex justify-between rounded-lg border border-slate-200 bg-white p-3 text-sm hover:bg-slate-50">
                <span>{s.role}{s.company ? ` · ${s.company}` : ""}</span>
                <span className="text-slate-500">{answered}/{s.questions.length} answered</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function InterviewPage() {
  return <RequireAuth><Sessions /></RequireAuth>;
}
