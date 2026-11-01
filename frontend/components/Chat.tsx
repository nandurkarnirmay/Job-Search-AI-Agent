"use client";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import JobCard from "@/components/JobCard";
import { CompanyCard, SalaryCard } from "@/components/Reports";
import { ATSCard, InterviewCard, PipelineBar, ReviewCard } from "@/components/Week4Cards";
import {
  api, ApiError, ChatExtras, ChatResponse, CompanyReport, createAlert, Intent, Job, SalaryReport, SearchParams,
  ThreadMessage, ThreadSummary,
} from "@/lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  intent?: Intent | null;
  params?: SearchParams | null;
  jobs?: Job[];
  company?: CompanyReport | null;
  salary?: SalaryReport | null;
  extras?: ChatExtras | null;
}

const EXAMPLES = [
  "Remote Python developer jobs in Bengaluru above 8 LPA",
  "Tell me about Infosys",
  "Average salary of a data analyst in Pune",
];
const FOLLOW_UPS = ["What about Hyderabad?", "Remove the salary filter", "Tell me about the first company",
  "How does my resume match the first job?", "Save the first job", "Prepare me for the first job interview"];

function fromThread(m: ThreadMessage): Msg {
  return { role: m.role, content: m.content, intent: m.intent, params: m.payload?.params, jobs: m.payload?.jobs ?? [],
    company: m.payload?.company, salary: m.payload?.salary, extras: m.payload?.extras };
}

function AlertButton({ params }: { params: SearchParams }) {
  const [state, setState] = useState<"idle" | "saving" | "done" | string>("idle");
  async function save() {
    setState("saving");
    try {
      await createAlert(params);
      setState("done");
    } catch (e) {
      setState(e instanceof ApiError ? e.message : "Couldn't create alert");
    }
  }
  if (state === "done") return <span className="text-xs text-green-700">Daily alert created. Manage it under Alerts.</span>;
  if (state !== "idle" && state !== "saving") return <span className="text-xs text-red-600">{state}</span>;
  return (
    <button onClick={save} disabled={state === "saving"}
      className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-white disabled:opacity-50">
      🔔 Alert me about new jobs like these
    </button>
  );
}

function Message({ m }: { m: Msg }) {
  if (m.role === "user") {
    return <div className="ml-auto max-w-[80%] rounded-lg bg-blue-600 px-3 py-2 text-sm text-white">{m.content}</div>;
  }
  const isSearch = m.intent === "job_search" || m.intent === "refine_search";
  return (
    <div className="space-y-3">
      <div className="max-w-[90%] whitespace-pre-line rounded-lg bg-white px-3 py-2 text-sm shadow-sm">{m.content}</div>
      {m.company && <CompanyCard r={m.company} />}
      {m.salary && <SalaryCard r={m.salary} />}
      {m.extras?.ats && <ATSCard m={m.extras.ats} />}
      {m.extras?.resume_review && <ReviewCard r={m.extras.resume_review} />}
      {m.extras?.interview && <InterviewCard s={m.extras.interview} />}
      {m.extras?.pipeline && <PipelineBar p={m.extras.pipeline} />}
      {isSearch && m.jobs && m.jobs.length > 0 && (
        <div className="space-y-2">
          {m.jobs.slice(0, 8).map((j) => <JobCard key={j.id} job={j} />)}
          {m.params && m.params.keywords && <AlertButton params={m.params} />}
        </div>
      )}
    </div>
  );
}

export default function Chat() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const loadThreads = useCallback(() => {
    api<ThreadSummary[]>("/chat/threads").then(setThreads).catch(() => setThreads([]));
  }, []);

  useEffect(loadThreads, [loadThreads]);
  useEffect(() => bottom.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy]);

  async function openThread(id: string) {
    if (!id) return newChat();
    setError(null);
    try {
      const t = await api<{ messages: ThreadMessage[] }>(`/chat/threads/${id}`);
      setThreadId(id);
      setMessages(t.messages.map(fromThread));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't open conversation");
    }
  }

  function newChat() {
    setThreadId(null);
    setMessages([]);
    setError(null);
  }

  async function deleteThread() {
    if (!threadId || !confirm("Delete this conversation?")) return;
    await api(`/chat/threads/${threadId}`, { method: "DELETE" }).catch(() => undefined);
    newChat();
    loadThreads();
  }

  async function send(text: string) {
    const message = text.trim();
    if (message.length < 2 || busy) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: message }]);
    setBusy(true);
    try {
      const r = await api<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify(threadId ? { message, thread_id: threadId } : { message }),
      });
      setMessages((m) => [...m, { role: "assistant", content: r.reply, intent: r.intent, params: r.params,
        jobs: r.jobs, company: r.company, salary: r.salary, extras: r.extras }]);
      if (!threadId) loadThreads();
      setThreadId(r.thread_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
      setMessages((m) => m.slice(0, -1));
      setInput(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button onClick={newChat} className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-white">+ New chat</button>
        {threads.length > 0 && (
          <select value={threadId ?? ""} onChange={(e) => openThread(e.target.value)}
            className="max-w-xs rounded border border-slate-300 px-2 py-1 text-sm">
            <option value="">Previous conversations…</option>
            {threads.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
        )}
        {threadId && <button onClick={deleteThread} className="text-xs text-slate-500 hover:text-red-600">Delete</button>}
      </div>

      <div className="min-h-[300px] space-y-4 rounded-lg bg-slate-100 p-4">
        {messages.length === 0 && (
          <div className="py-8 text-center text-sm text-slate-600">
            <p>Ask for jobs, a company, or a salary. Follow-up questions remember the conversation.</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex} onClick={() => send(ex)}
                  className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs hover:bg-slate-50">{ex}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => <Message key={i} m={m} />)}
        {busy && <p className="text-sm text-slate-500">Thinking…</p>}
        <div ref={bottom} />
      </div>

      {messages.length > 0 && !busy && (
        <div className="mt-3 flex flex-wrap gap-2">
          {FOLLOW_UPS.map((f) => (
            <button key={f} onClick={() => send(f)}
              className="rounded-full border border-slate-300 px-3 py-1 text-xs hover:bg-white">{f}</button>
          ))}
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      <form onSubmit={(e: FormEvent) => { e.preventDefault(); send(input); }} className="mt-3 flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={500}
          placeholder="Ask about jobs, a company, or salaries…" className="flex-1 rounded border border-slate-300 px-3 py-2" />
        <button disabled={busy} className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50">Send</button>
      </form>
    </div>
  );
}
