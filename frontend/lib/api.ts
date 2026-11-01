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
  // JSON bodies only: for FormData (file upload) the browser must set the multipart boundary itself
  if (typeof init.body === "string" && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
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

export type Intent = "job_search" | "refine_search" | "company_research" | "salary_research" | "resume_review"
  | "resume_match" | "interview_prep" | "track_application" | "applications_status" | "help";

export interface SalaryStats {
  n: number;
  p25: number;
  median: number;
  p75: number;
  min: number;
  max: number;
}

export interface SalaryReport {
  role: string;
  city: string | null;
  experience_years: number | null;
  listings: SalaryStats | null;
  market: SalaryStats | null;
  notes: string[];
}

export interface CompanyReport {
  name: string;
  wiki: { title: string; description: string | null; extract: string; url: string | null } | null;
  open_roles: number | null;
  sample_roles: { title: string; location: string; url: string }[];
  top_cities: string[];
  disclosed_salary: SalaryStats | null;
  sources: string[];
  notes: string[];
}

export interface ChatResponse {
  thread_id: string;
  reply: string;
  intent: Intent;
  params: SearchParams | null;
  jobs: Job[];
  company: CompanyReport | null;
  salary: SalaryReport | null;
  extras: ChatExtras | null;
  parser: "llm" | "rules";
}

export interface ThreadSummary {
  id: string;
  title: string;
  updated_at: string;
}

export interface ThreadMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  intent: Intent | null;
  payload: {
    params: SearchParams | null; jobs: Job[]; company: CompanyReport | null; salary: SalaryReport | null;
    extras?: ChatExtras | null;
  } | null;
  created_at: string;
}

export interface Alert {
  id: number;
  name: string;
  params: SearchParams;
  frequency: "daily" | "weekly";
  active: boolean;
  last_run_at: string | null;
  created_at: string;
}

export interface AlertPreview {
  total: number;
  new: number;
  jobs: Job[];
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
  career_goal: string | null;
  target_roles: string[];
  open_to_relocation: boolean | null;
}

/** Human label for a search, used as the default alert name. */
export function describeSearch(p: Partial<SearchParams>): string {
  const bits = [p.keywords];
  if (p.city) bits.push(`in ${p.city}`);
  if (p.work_mode) bits.push(`(${p.work_mode})`);
  if (p.min_salary_lpa != null) bits.push(`${p.min_salary_lpa}+ LPA`);
  return bits.filter(Boolean).join(" ").slice(0, 80);
}

export async function createAlert(params: Partial<SearchParams> & { keywords: string }): Promise<Alert> {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== null && v !== "" && v !== undefined));
  return api<Alert>("/alerts", {
    method: "POST",
    body: JSON.stringify({ name: describeSearch(params), params: clean, frequency: "daily" }),
  });
}

// ---------- Week 4 ----------
export interface ATSMatch {
  score: number;
  skills_score: number;
  title_score: number;
  structure_score: number;
  job_title: string;
  company: string | null;
  matched_required: string[];
  missing_required: string[];
  matched_preferred: string[];
  missing_preferred: string[];
  suggestions: string[];
  notes: string[];
}

export interface ResumeReview {
  role: string | null;
  skills: string[];
  warnings: string[];
  sections: Record<string, boolean>;
  jobs_sampled: number;
  demand: { skill: string; share: number; have: boolean }[];
  notes: string[];
}

export interface ResumeInfo {
  filename: string;
  kind: "pdf" | "docx";
  pages: number;
  word_count: number;
  skills: string[];
  sections: Record<string, boolean>;
  has_contact: boolean;
  warnings: string[];
  uploaded_at: string;
}

export const APP_STATUSES = ["saved", "applied", "interview", "offer", "rejected", "withdrawn"] as const;
export type AppStatus = (typeof APP_STATUSES)[number];

export interface Application {
  id: number;
  job_id: string | null;
  title: string;
  company: string;
  location: string;
  url: string | null;
  salary_min_lpa: number | null;
  salary_max_lpa: number | null;
  status: AppStatus;
  notes: string | null;
  next_action_on: string | null;
  history: { status: AppStatus; at: string }[];
  created_at: string;
  updated_at: string;
}

export interface InterviewQuestion {
  id: string;
  text: string;
  category: "hr" | "behavioural" | "technical";
  skill: string | null;
  source: "bank" | "llm";
}

export interface AnswerFeedback {
  score: number;
  word_count: number;
  criteria: { name: string; score: number; comment: string }[];
  key_points_hit: string[];
  key_points_missed: string[];
  tips: string[];
  coach_comment: string | null;
}

export interface InterviewSession {
  id: number;
  role: string;
  company: string | null;
  questions: InterviewQuestion[];
  answers: Record<string, { answer: string; feedback: AnswerFeedback }>;
  notes: string[];
  created_at: string;
}

export interface ChatExtras {
  ats: ATSMatch | null;
  resume_review: ResumeReview | null;
  interview: InterviewSession | null;
  application: Application | null;
  pipeline: Record<AppStatus, number> | null;
}

export interface AlertRun {
  id: number;
  ran_at: string;
  new_jobs: number;
  emailed: boolean;
  error: string | null;
  digest: { id: string; title: string; company: string; location: string; url: string }[];
}

export function saveJob(jobId: string): Promise<Application> {
  return api<Application>("/applications", { method: "POST", body: JSON.stringify({ job_id: jobId }) });
}
