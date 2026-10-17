# Architecture (Week 2)

```
Next.js (Vercel) ──HTTPS + JWT──► FastAPI (Render)
                                   ├─ /auth, /me/profile ──► PostgreSQL (Neon): users, profiles, search_logs
                                   ├─ /chat ──► LangGraph: parse_query ─► search ─► respond
                                   │                 │ Gemini (rule parser fallback)
                                   ├─ /jobs/search ──► Search service ──► Redis cache (Upstash)
                                   │                        └─► Aggregator ─┬─► Adzuna (India)
                                   │                                         └─► JSearch (RapidAPI)
                                   └─ /health, /metrics, /stats
```

**Search flow.** Raw source results are cached by (keywords, city, page) for 15 min; filters run after the
cache, so changing a filter costs no API call. Sources are queried in parallel; each has retries with
exponential backoff (429/5xx/timeouts only), a 1 req/s client-side throttle and a circuit breaker (3 failed
searches → skipped for 60 s). If some sources fail the user gets partial results plus a notice; if all fail,
a clean 503.

**Filtering policy.** Indian listings often omit salary/experience. A job *known* to violate a filter is
dropped; a job with *unknown* values is kept but ranked below jobs known to match.

**Agent.** Gemini returns structured `SearchParams`. Numbers the LLM produces are kept only if the rule
parser also found them in the text or they came from the user's profile, which blocks hallucinated filters.
Without an API key, or if the LLM call fails, the rule parser is used.

**Errors.** Every error is `{"error": {"code", "message", "request_id"}}`; the request ID is also in the
`x-request-id` header and in the JSON logs, so a user's error can be traced in Render logs.

**Next (Weeks 3–4).** A router node sends each message to the right tool node: job search, company
research, resume analysis, interview prep, salary research.
