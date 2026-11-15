"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { setToken } from "@/lib/api";
import { useLoggedIn } from "@/lib/useAuth";

const LINKS: [string, string][] = [
  ["/dashboard", "Dashboard"], ["/search", "Search"], ["/career", "Career"], ["/resume", "Resume"],
  ["/interview", "Interview"], ["/applications", "Tracker"], ["/alerts", "Alerts"], ["/profile", "Profile"],
  ["/settings", "Settings"],
];

export default function Nav() {
  const loggedIn = useLoggedIn();
  const router = useRouter();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const logout = () => { setToken(null); setOpen(false); router.push("/login"); };
  const link = (href: string, label: string) => (
    <Link key={href} href={href} onClick={() => setOpen(false)}
      className={path?.startsWith(href) ? "font-semibold text-blue-700" : "hover:text-blue-700"}>{label}</Link>
  );
  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href={loggedIn ? "/dashboard" : "/"} className="font-semibold">Job Search AI Agent</Link>
        {loggedIn && (
          <button className="rounded border border-slate-300 px-2 py-1 text-sm md:hidden" aria-expanded={open}
            aria-label="Menu" onClick={() => setOpen(!open)}>☰</button>
        )}
        <div className="hidden items-center gap-x-4 text-sm md:flex">
          {loggedIn && <>{LINKS.map(([h, l]) => link(h, l))}
            <button onClick={logout} className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-100">Log out</button></>}
          {loggedIn === false && (
            <>
              <Link href="/login" className="hover:text-blue-700">Log in</Link>
              <Link href="/register" className="rounded bg-blue-600 px-3 py-1 text-white hover:bg-blue-700">Sign up</Link>
            </>
          )}
        </div>
        {loggedIn === false && (
          <div className="flex gap-3 text-sm md:hidden">
            <Link href="/login">Log in</Link>
            <Link href="/register" className="rounded bg-blue-600 px-3 py-1 text-white">Sign up</Link>
          </div>
        )}
      </nav>
      {loggedIn && open && (
        <div className="flex flex-col gap-2 border-t border-slate-200 px-4 py-3 text-sm md:hidden">
          {LINKS.map(([h, l]) => link(h, l))}
          <button onClick={logout} className="self-start rounded border border-slate-300 px-3 py-1">Log out</button>
        </div>
      )}
    </header>
  );
}
