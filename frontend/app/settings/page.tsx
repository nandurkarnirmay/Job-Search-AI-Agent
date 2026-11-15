"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import RequireAuth from "@/components/RequireAuth";
import { api, ApiError, download, setToken } from "@/lib/api";

function Settings() {
  const router = useRouter();
  const [msg, setMsg] = useState<string | null>(null);

  async function exportData() {
    setMsg(null);
    try {
      await download("/me/export", "my-job-search-data.json");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Export failed");
    }
  }

  async function deleteAccount() {
    if (!confirm("Delete your account and ALL your data (resume, tracker, chats, interview practice)? This can't be undone.")) return;
    try {
      await api("/auth/me", { method: "DELETE" });
      setToken(null);
      router.push("/");
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Deletion failed");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Privacy & data</h1>
      <section className="space-y-2 rounded-lg border border-slate-200 bg-white p-5 text-sm">
        <h2 className="font-semibold">How your data is handled</h2>
        <ul className="list-disc space-y-1 pl-5 text-slate-700">
          <li>Resume files are never stored: only the text (with email and phone removed) and the parsed skills.</li>
          <li>Resume text, interview answers, chat messages and notes are encrypted at rest.</li>
          <li>Conversations inactive for 180 days and search history older than 90 days are deleted automatically.</li>
          <li>Everything you save is private to your account. GitHub analysis reads public data only.</li>
        </ul>
      </section>
      <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 text-sm">
        <h2 className="font-semibold">Your data</h2>
        <button onClick={exportData} className="rounded border border-slate-300 px-3 py-1.5 hover:bg-slate-50">Download all my data (JSON)</button>
        <div>
          <button onClick={deleteAccount} className="rounded border border-red-300 px-3 py-1.5 text-red-700 hover:bg-red-50">Delete my account</button>
        </div>
        {msg && <p className="text-red-600">{msg}</p>}
      </section>
    </div>
  );
}

export default function SettingsPage() {
  return <RequireAuth><Settings /></RequireAuth>;
}
