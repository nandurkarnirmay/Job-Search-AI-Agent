import Link from "next/link";

export default function Home() {
  return (
    <section className="py-12 text-center">
      <h1 className="text-4xl font-bold">Find jobs in India by just asking</h1>
      <p className="mx-auto mt-4 max-w-xl text-slate-600">
        “Remote Python jobs in Bengaluru above 8 LPA for a fresher.” The agent turns that into a search across
        multiple job sources and filters by city, experience, salary in LPA, work mode and notice period.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/register" className="rounded bg-blue-600 px-5 py-2 text-white hover:bg-blue-700">Get started</Link>
        <Link href="/login" className="rounded border border-slate-300 px-5 py-2 hover:bg-white">Log in</Link>
      </div>
    </section>
  );
}
