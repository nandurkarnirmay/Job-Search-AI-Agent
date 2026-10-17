"use client";
import { useEffect, useState } from "react";
import { getToken } from "./api";

/** Returns null while checking, then true/false. Re-renders on login/logout. */
export function useLoggedIn(): boolean | null {
  const [loggedIn, setLoggedIn] = useState<boolean | null>(null);
  useEffect(() => {
    const update = () => setLoggedIn(!!getToken());
    update();
    window.addEventListener("auth-change", update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener("auth-change", update);
      window.removeEventListener("storage", update);
    };
  }, []);
  return loggedIn;
}
