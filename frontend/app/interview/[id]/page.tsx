"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import VoiceInput, { speechSupported, VoiceResult } from "@/components/VoiceInput";
import { AnswerFeedback, api, ApiError, InterviewQuestion, InterviewReport, InterviewSession } from "@/lib/api";

const CATEGORY: Record<string, string> = { hr: "HR", behavioural: "Behavioural", technical: "Technical" };

function Feedback({ f }: { f: AnswerFeedback }) {
  return (
    <div className="space-y-2 rounded bg-slate-50 p-3 text-sm">
      <p className="font-semibold">Score: {f.score}/5 <span className="font-normal text-slate-500">· {f.word_count} words
        {f.speech ? ` · ${f.speech.words_per_minute} words/min · ${f.speech.filler_per_100_words} fillers/100 words` : ""}</span></p>
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

function Question({ sid, q, saved, onFollowup }: { sid: number; q: InterviewQuestion;
  saved?: { answer: string; feedback: AnswerFeedback }; onFollowup: (parent: string, f: InterviewQuestion) => void }) {
  const [answer, setAnswer] = useState(saved?.answer ?? "");
  const [fb, setFb] = useState<AnswerFeedback | null>(saved?.feedback ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voice, setVoice] = useState(false);

  async function submit(body: { answer: string; duration_seconds?: number; long_pauses?: number }) {
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ feedback: AnswerFeedback; followup: InterviewQuestion | null }>(
        `/interview/sessions/${sid}/questions/${q.id}/answer`, { method: "POST", body: JSON.stringify(body) });
      setFb(r.feedback);
      if (r.followup) onFollowup(q.id, r.followup);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't evaluate");
    } finally {
      setBusy(false);
    }
  }

  const fromVoice = (v: VoiceResult) => {
    setAnswer(v.transcript);
    submit({ answer: v.transcript, duration_seconds: v.durationSeconds, long_pauses: v.longPauses });
  };

  return (
    <div className={`space-y-2 rounded-lg border bg-white p-4 ${q.source === "followup" ? "ml-6 border-blue-200" : "border-slate-200"}`}>
      <p className="text-xs uppercase tracking-wide text-slate-500">
        {q.source === "followup" ? "Follow-up" : CATEGORY[q.category]}{q.skill ? ` · ${q.skill}` : ""}
        {q.source === "llm" ? " · AI-generated" : ""}
      </p>
      <p className="font-medium">{q.text}</p>
      <div className="flex gap-2 text-xs">
        <button onClick={() => setVoice(false)} className={!voice ? "font-semibold" : "text-slate-500"}>Type</button>
        <span className="text-slate-300">|</span>
        <button onClick={() => setVoice(true)} className={voice ? "font-semibold" : "text-slate-500"} disabled={!speechSupported()}
          title={speechSupported() ? "" : "Voice needs Chrome, Edge or Safari"}>Speak</button>
      </div>
      {voice ? <VoiceInput onDone={fromVoice} /> : (
        <>
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={5} maxLength={5000}
            placeholder="Type your answer as you would say it…" className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          <button onClick={() => submit({ answer })} disabled={busy || !answer.trim()}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
            {busy ? "Checking…" : fb ? "Re-check" : "Get feedback"}
          </button>
        </>
      )}
      {busy && voice && <p className="text-sm text-slate-500">Checking…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {fb && <Feedback f={fb} />}
    </div>
  );
}

function Report({ r }: { r: InterviewReport }) {
  return (
    <div className="space-y-2 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm">
      <h2 className="font-semibold">Session report: {r.answered}/{r.total} answered{r.average_score != null ? ` · average ${r.average_score}/5` : ""}</h2>
      {Object.keys(r.by_category).length > 0 && <p>By type: {Object.entries(r.by_category).map(([k, v]) => `${CATEGORY[k] ?? k} ${v}/5`).join(" · ")}</p>}
      {r.average_wpm != null && <p>Average pace: {r.average_wpm} words/min (aim for 110–160)</p>}
      {r.weakest.length > 0 && <p><b>Work on:</b> {r.weakest.map((w) => `“${w.question}” (${w.score}/5)`).join("; ")}</p>}
      {r.recurring_tips.length > 0 && <ul className="list-disc pl-5">{r.recurring_tips.map((t) => <li key={t}>{t}</li>)}</ul>}
      <ul className="list-disc pl-5">{r.next_steps.map((t) => <li key={t}>{t}</li>)}</ul>
    </div>
  );
}

function Practice() {
  const { id } = useParams<{ id: string }>();
  const [s, setS] = useState<InterviewSession | null>(null);
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<InterviewSession>(`/interview/sessions/${id}`).then(setS)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Couldn't load"));
  }, [id]);

  const addFollowup = (parent: string, f: InterviewQuestion) => setS((cur) => {
    if (!cur || cur.questions.some((q) => q.id === f.id)) return cur;
    const i = cur.questions.findIndex((q) => q.id === parent);
    return { ...cur, questions: [...cur.questions.slice(0, i + 1), f, ...cur.questions.slice(i + 1)] };
  });

  const loadReport = () => api<InterviewReport>(`/interview/sessions/${id}/report`).then(setReport)
    .catch((e) => setError(e instanceof ApiError ? e.message : "Couldn't load the report"));

  if (error) return <p className="text-red-600">{error}</p>;
  if (!s) return <p className="text-slate-500">Loading…</p>;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold">{s.role}{s.company ? ` · ${s.company}` : ""}</h1>
          <p className="text-sm text-slate-600">Answer by typing or by voice. The interviewer asks a follow-up when an answer
            leaves something out. Scores are rule-based and reproducible; the coach line (if shown) is AI-written.</p>
        </div>
        <button onClick={loadReport} className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-white">Session report</button>
      </div>
      {report && <Report r={report} />}
      {s.questions.map((q) => <Question key={q.id} sid={s.id} q={q} saved={s.answers[q.id]} onFollowup={addFollowup} />)}
    </div>
  );
}

export default function PracticePage() {
  return <RequireAuth><Practice /></RequireAuth>;
}
