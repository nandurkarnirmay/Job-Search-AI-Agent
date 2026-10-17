export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "jsa_token";

// Week 2: token in localStorage for simplicity. Week 7 hardening: move to an httpOnly cookie.
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage blocked: user just has to log in again */
  }
  window.dispatchEvent(new Event("auth-change"));
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the server. The backend may be waking up; retry in 30s.");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error ?? {};
    if (res.status === 401) setToken(null);
    throw new ApiError(res.status, err.code ?? "error", err.message ?? `Request failed (${res.status})`);
  }
  return data as T;
}

export type WorkMode = "remote" | "hybrid" | "onsite";

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  url: string;
  source: string;
  description: string;
  salary_min_lpa: number | null;
  salary_max_lpa: number | null;
  experience_min_years: number | null;
  experience_max_years: number | null;
  work_mode: WorkMode | null;
  notice_period_days: number | null;
  posted_at: string | null;
}

export interface SearchParams {
  keywords: string;
  city: string | null;
  max_experience_years: number | null;
  min_salary_lpa: number | null;
  work_mode: WorkMode | null;
  notice_period_days: number | null;
  page: number;
}

export interface SearchResponse {
  params: SearchParams;
  jobs: Job[];
  count: number;
  sources_ok: string[];
  sources_failed: string[];
  cache_hit: boolean;
  latency_ms: number;
}

export interface ChatResponse {
  reply: string;
  params: SearchParams | null;
  jobs: Job[];
  parser: "llm" | "rules";
}

export interface Profile {
  full_name: string | null;
  current_city: string | null;
  preferred_cities: string[];
  experience_years: number | null;
  skills: string[];
  expected_lpa: number | null;
  notice_period_days: number | null;
  work_mode: WorkMode | "any" | null;
}
