"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import { AnswerFeedback, api, ApiError, InterviewQuestion, InterviewSession } from "@/lib/api";

const CATEGORY: Record<string, string> = { hr: "HR", behavioural: "Behavioural", technical: "Technical" };

function Feedback({ f }: { f: AnswerFeedback }) {
  return (
    <div className="space-y-2 rounded bg-slate-50 p-3 text-sm">
      <p className="font-semibold">Score: {f.score}/5 <span className="font-normal text-slate-500">· {f.word_count} words</span></p>
      <ul className="space-y-0.5">
        {f.criteria.map((c) => (
          <li key={c.name}><span className={c.score >= 0.7 ? "text-green-700" : "text-amber-700"}>
            {c.score >= 0.7 ? "✓" : "△"}</span> <b>{c.name}</b>: {c.comment}</li>
        ))}
      </ul>
      {f.tips.length > 0 && <ul className="list-disc pl-5 text-slate-700">{f.tips.map((t) => <li key={t}>{t}</li>)}</ul>}
      {f.coach_comment && <p className="italic text-slate-600">Coach: {f.coach_comment}</p>}
    </div>
  );
}

function Question({ sid, q, saved }: { sid: number; q: InterviewQuestion; saved?: { answer: string; feedback: AnswerFeedback } }) {
  const [answer, setAnswer] = useState(saved?.answer ?? "");
  const [fb, setFb] = useState<AnswerFeedback | null>(saved?.feedback ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ feedback: AnswerFeedback }>(`/interview/sessions/${sid}/questions/${q.id}/answer`, {
        method: "POST", body: JSON.stringify({ answer }),
      });
      setFb(r.feedback);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't evaluate");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">
        {CATEGORY[q.category]}{q.skill ? ` · ${q.skill}` : ""}{q.source === "llm" ? " · AI-generated" : ""}
      </p>
      <p className="font-medium">{q.text}</p>
      <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={5} maxLength={5000}
        placeholder="Type your answer as you would say it…" className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
      <button onClick={submit} disabled={busy || !answer.trim()}
        className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
        {busy ? "Checking…" : fb ? "Re-check" : "Get feedback"}
      </button>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {fb && <Feedback f={fb} />}
    </div>
  );
}

function Practice() {
  const { id } = useParams<{ id: string }>();
  const [s, setS] = useState<InterviewSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<InterviewSession>(`/interview/sessions/${id}`).then(setS)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Couldn't load"));
  }, [id]);
  if (error) return <p className="text-red-600">{error}</p>;
  if (!s) return <p className="text-slate-500">Loading…</p>;
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">{s.role}{s.company ? ` · ${s.company}` : ""}</h1>
        <p className="text-sm text-slate-600">Answer in 1–2 minutes' worth of words. Feedback is rule-based and
          reproducible; the coach line (if shown) is AI-written.</p>
      </div>
      {s.questions.map((q) => <Question key={q.id} sid={s.id} q={q} saved={s.answers[q.id]} />)}
    </div>
  );
}

export default function PracticePage() {
  return <RequireAuth><Practice /></RequireAuth>;
}
