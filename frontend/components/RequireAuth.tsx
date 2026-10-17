"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useLoggedIn } from "@/lib/useAuth";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const loggedIn = useLoggedIn();
  const router = useRouter();
  useEffect(() => {
    if (loggedIn === false) router.replace("/login");
  }, [loggedIn, router]);
  return loggedIn ? <>{children}</> : <p className="text-slate-500">Loading…</p>;
}
