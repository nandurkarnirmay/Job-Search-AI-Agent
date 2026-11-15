"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useLoggedIn } from "@/lib/useAuth";

const FEATURES = [
  ["Ask in plain English", "“Remote Python jobs in Bengaluru above 8 LPA for a fresher” searches Adzuna, JSearch and Jooble at once."],
  ["Salary & negotiation", "Benchmarks by experience band from live listings, and a counter-offer with an email script."],
  ["Resume & GitHub", "ATS match against a job, skill demand, and a check of what your GitHub actually proves."],
  ["Mock interviews", "Type or speak your answers; get scored on structure, pace and fillers, with follow-up questions."],
  ["Career roadmap", "Skills your target role asks for, in 6-week phases with free resources and a project each."],
  ["Tracker & calendar", "Applications pipeline, interview reminders by email, and a calendar feed for Google/Outlook."],
];

export default function Home() {
  const loggedIn = useLoggedIn();
  const router = useRouter();
  useEffect(() => { if (loggedIn) router.replace("/dashboard"); }, [loggedIn, router]);
  return (
    <section className="py-12">
      <div className="text-center">
        <h1 className="text-4xl font-bold">Your job search in India, in one place</h1>
        <p className="mx-auto mt-4 max-w-xl text-slate-600">
          Search, salary, resume, interview practice and tracking: one assistant built for LPA, notice periods and
          Indian cities.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/register" className="rounded bg-blue-600 px-5 py-2 text-white hover:bg-blue-700">Get started</Link>
          <Link href="/login" className="rounded border border-slate-300 px-5 py-2 hover:bg-white">Log in</Link>
        </div>
      </div>
      <div className="mx-auto mt-12 grid max-w-4xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(([t, d]) => (
          <div key={t} className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="font-semibold">{t}</h2>
            <p className="mt-1 text-sm text-slate-600">{d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
