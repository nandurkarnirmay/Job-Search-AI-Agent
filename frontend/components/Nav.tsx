"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { setToken } from "@/lib/api";
import { useLoggedIn } from "@/lib/useAuth";

export default function Nav() {
  const loggedIn = useLoggedIn();
  const router = useRouter();
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="font-semibold">Job Search AI Agent</Link>
        <div className="flex items-center gap-4 text-sm">
          {loggedIn && (
            <>
              <Link href="/search" className="hover:text-blue-700">Search</Link>
              <Link href="/profile" className="hover:text-blue-700">Profile</Link>
              <button
                onClick={() => { setToken(null); router.push("/login"); }}
                className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-100"
              >
                Log out
              </button>
            </>
          )}
          {loggedIn === false && (
            <>
              <Link href="/login" className="hover:text-blue-700">Log in</Link>
              <Link href="/register" className="rounded bg-blue-600 px-3 py-1 text-white hover:bg-blue-700">Sign up</Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
