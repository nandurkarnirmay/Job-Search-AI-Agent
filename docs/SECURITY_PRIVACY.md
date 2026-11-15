# Privacy and security assessment (Week 7)

Scope: the deployed app (Next.js on Vercel, FastAPI services on Render, Neon Postgres, Upstash Redis) and the
data it holds about job seekers. Method: data inventory → threat model → controls → tested evidence → known gaps.
This is a self-assessment by the team, not an external audit or penetration test.

## 1. Data inventory
| Data | Where | Sensitivity | Protection | Retention |
|---|---|---|---|---|
| Email, password | `users` | high | password bcrypt-hashed (cost 12); email plaintext (needed for login) | until account deleted |
| Profile (cities, experience, expected/current LPA, notice, skills, GitHub username) | `profiles` | medium | access-controlled | until deleted |
| Resume text | `resumes.text` | **high** (career history) | file never stored; email/phone redacted; **encrypted** | until deleted / replaced |
| Chat messages | `chat_messages.content` | high (offers, salaries) | **encrypted** | 180 days idle, then purged |
| Interview answers | `interview_sessions.answers` | medium | **encrypted** | until deleted |
| Tracker + event notes | `applications.notes`, `calendar_events.notes` | medium | **encrypted** | until deleted |
| Event titles/times, tracker companies & statuses | tables | medium | access-controlled (needed for queries, reminders, the feed) | until deleted |
| Search logs (keywords, filters, latency) | `search_logs` | low | admin-only | 90 days |
| Alert runs | `alert_runs` | low | owner-only | 60 days |
| Calendar feed token | `users.calendar_token` | high (bearer secret) | 256-bit random, unique, rotatable, revocable, excluded from export | until revoked |
| Voice audio | **not received** | | browser-side STT (see §5) | n/a |

## 2. Threat model (STRIDE, abridged)
| Threat | Example | Control | Status |
|---|---|---|---|
| Spoofing | password guessing | bcrypt; 30/min per IP **and 10/min per account** (Week 7: IP alone was spoofable via `X-Forwarded-For`) | ✅ tested |
| Spoofing | stolen JWT | 24 h expiry, HS256 with a generated secret | ⚠️ token in localStorage (§6) |
| Tampering | forged job details saved to tracker | saved jobs come from the server cache, not the client | ✅ tested |
| Repudiation | | request IDs in every log line and error | ✅ |
| Information disclosure | user A reads B's resume/tracker/events | every query filters by owner; foreign ids return 404, not 403 | ✅ tested per resource |
| Information disclosure | DB dump / backup leak | field encryption on the free-text personal columns | ✅ tested (raw SQL sees ciphertext) |
| Information disclosure | metrics scraped | `/metrics` 404 without `X-Metrics-Token` | ✅ tested |
| Information disclosure | XSS via third-party job text | React escaping; only `http(s)` links rendered; emails HTML-escaped; CSP on the API | ✅ tested (emails) |
| Denial of service | zip-bomb DOCX, huge PDF | 2 MB, 6 pages, 20 MB unpacked cap, magic-byte check | ✅ tested |
| Denial of service | API quota exhaustion | per-user rate limits, cache, fallback source only on demand | ✅ |
| Elevation of privilege | non-admin hits `/analytics/system` | admin allow-list | ✅ tested |
| LLM prompt injection | job text tells Gemini to invent salaries | numbers never come from the LLM; LLM output rejected if it names entities not in the message or adds numbers not in the source | ✅ tested |

## 3. Controls in detail
**Encryption at rest.** Fernet (AES-128-CBC + HMAC-SHA256, authenticated) per field, via SQLAlchemy types, so
every read/write path is covered without per-endpoint code. Keys from `FIELD_ENCRYPTION_KEYS` (comma list; first
encrypts, all decrypt → rotation without downtime). The key string is hashed (SHA-256) into a Fernet key, so it
**must be high-entropy random**, not a passphrase. Production refuses to start without it. Neon also encrypts
storage at rest; ours protects against DB-level leaks (dumps, branch copies, a compromised DB credential).
Not protected: an attacker with the running app's environment (has the key).

**Transport and headers.** HTTPS everywhere (Vercel/Render). API: `Content-Security-Policy: default-src 'none'`,
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, HSTS in production.
Frontend: same, `Permissions-Policy` allows the microphone for our origin only.

**Secrets.** Only in Render/Vercel settings and GitHub Secrets; `.env` is git-ignored; CI uses dummy values.
GitHub token needs no permissions (public data).

**Third-party data flow.** Gemini receives: chat messages the rule router can't classify, interview answers (for
the optional coaching comment and follow-up wording), role and skills (for extra interview questions), and Wikipedia text to rephrase. It never receives resume text, salaries
from your profile, or account data. GitHub/Adzuna/JSearch/Jooble receive search keywords only.

## 4. Privacy (aligned with India's DPDP Act 2023 principles; not a legal opinion)
| Principle | How |
|---|---|
| Purpose limitation / minimisation | resume files discarded, contacts redacted, no audio, no scraping |
| Right to access | `GET /me/export`: all data as JSON (excludes password hash and feed token) |
| Right to erasure | `DELETE /auth/me` cascades to every table |
| Storage limitation | automatic purge (chats 180 d, logs 90 d, alert runs 60 d) |
| Accuracy / transparency | every statistic shows its sample size; estimates labelled; "not enough data" instead of guesses |
| Data location | Neon and Upstash in Singapore/Mumbai, Render Singapore; **not** guaranteed in India |
We have no consent banner or published privacy policy page yet (Week 8).

## 5. Voice
Speech-to-text uses the browser's Web Speech API. Our server receives only the transcript and timing. **But
Chrome sends the audio to Google's speech service** (Safari to Apple). The UI says so next to the button, and
typing is always available.

## 6. Known gaps (ranked)
| # | Gap | Risk | Plan |
|---|---|---|---|
| 1 | JWT in `localStorage` | an XSS bug would expose the token | httpOnly SameSite cookie through the same-origin gateway (Week 8); meanwhile no third-party scripts, React escaping |
| 2 | Services share one DB user | a compromised resume service can read all tables | per-service DB roles (Neon supports roles) |
| 3 | Leftmost `X-Forwarded-For` used for IP limits | IP limit bypassable (account limit now covers login) | trust only the hop added by Render |
| 4 | No MFA, no email verification, no password reset | account takeover via reused password | email verification + reset (Week 8 if time) |
| 5 | Emails, event titles and company names not encrypted | readable in a DB leak | acceptable: needed for login/queries/reminders |
| 6 | Single encryption key in the app environment | key compromise = all fields | rotation supported; KMS not available on free tier |
| 7 | Dependencies not scanned | known-CVE libraries | enable GitHub Dependabot (free) |

## 7. Evidence
Automated tests (`backend/tests/test_week7.py` and earlier weeks): ciphertext in raw SQL, export completeness and
secret exclusion, retention boundaries, security headers, metrics token, per-account login cap with spoofed IPs,
owner isolation for every resource, admin-only endpoints, upload limits, HTML escaping in emails.
