# Week 3: Multi-tool career agent, conversation memory and job alerts

## What we did
This week the chat assistant became a multi-tool agent. Before, every message was treated as a job search. Now
a router node in the LangGraph workflow decides what the user wants and sends the message to one of five
paths: a new job search, a refinement of the previous search, company research, salary research, or help.
The router is rule-based first. Gemini is asked only when no rule matches, which saves free-tier quota and
latency. The LLM's choice is accepted only if it is consistent with the message: it cannot route to research on
a company the user never named.

**Conversation memory.** Conversations are now stored in PostgreSQL as threads, with the last search and its
results. Follow-ups work as a user expects: "what about Pune?", "only remote", "show more",
"tell me about the second company", or "what's the salary for the first one". Users can reopen or delete past
conversations.

**Company research tool.** For "tell me about Infosys" the agent combines three things:
- a Wikipedia overview, with matching that handles Indian abbreviations (TCS → Tata Consultancy Services,
  L&T → Larsen & Toubro) and rejects non-company pages
- the company's current openings in our job sources, with top cities
- disclosed salaries from those openings

Gemini may only rephrase the Wikipedia text. If its version contains any number that isn't in the source, it is
discarded and the original sentences are shown. Glassdoor and AmbitionBox have no public APIs, so the agent
states that reviews are not included instead of inventing them.

**Salary research tool.** For "average salary of a data analyst in Pune" the agent reports the median, the
middle 50% and the range, in LPA. It uses two sources: salaries disclosed in current listings, and Adzuna's
salary histogram (labelled as including estimates). Every figure shows its sample size. With fewer than 3 data
points the agent says there isn't enough data instead of guessing. These numbers are computed in code and never
pass through the LLM.

**Job alerts.** Users can save any search as a daily or weekly alert, then pause, edit, delete or preview it
(up to 5 per user). Alerts remember which jobs were already sent, matched by title, company and city, so a job
re-posted on a second site isn't reported as new. Scheduled sending by email is planned for Week 4.

**Profile.** Users can now save a career goal, target roles and whether they are open to relocation.
"Show me jobs" with no role searches the user's main target role.

**Engineering.**
- **Database migrations:** we introduced Alembic and wrote the two migrations ourselves. Week 2's database is
  detected and upgraded in place on deploy, with no data loss.
- **Shared resilience layer:** the retry, timeout and circuit-breaker code is now shared by every external API
  (job sources, Wikipedia, salary data). A malformed API response now counts as a source failure.
- **Tests:** we added about 60 test cases, covering routing phrasings, follow-ups and ordinal references,
  company and salary tools, alert new-job detection and scheduling, privacy (users can't open each other's
  conversations or alerts), and migrations (a fresh database matches the models; a Week 2 database upgrades
  safely).
- **CI:** now runs the migrations against PostgreSQL twice, to prove they are idempotent.
- **Monitoring:** new metrics count chat intents (rules vs LLM routing), LLM outputs rejected by the grounding
  checks, and alert runs.

## Contributions
| Member | Work this week |
|---|---|
| Member 1 | Router, LangGraph workflow, LLM grounding checks |
| Member 2 | Wikipedia and salary-histogram clients, shared resilience layer, salary statistics |
| Member 3 | Conversation UI, company and salary cards, alerts page, profile fields |
| Member 4 | Threads and alerts data model and API, Alembic migrations, tests, CI |

## Challenges and decisions
- **No reviews API.** We chose to state that reviews and ratings are missing rather than let the LLM generate
  them. A career tool that invents an employer's reputation does real harm.
- **Keeping the LLM honest.** Every LLM output is checked against its source: numbers in a company overview
  must appear in the Wikipedia text, and a routed company must appear in the user's message. Salary figures
  never go through the LLM at all.
- **Free-tier limits.** Rules-first routing and caching (company reports 6 h, salary histograms 6 h, job
  results 15 min) keep us inside the Gemini, Adzuna and RapidAPI quotas.

## Plan for next week (Week 4, checkpoint: agent with 4+ career tools)
- **Resume tool:** PDF/DOCX upload, text extraction, skill extraction, and an ATS keyword-match score against a
  chosen job, with missing keywords.
- **Interview-prep tool:** role-specific questions and feedback on typed answers.
- **Application tracker:** save a job and move it through Saved → Applied → Interview → Offer/Rejected.
- **Alert delivery:** Celery beat runs due alerts and emails new jobs.
- **Router follow-ups:** follow-ups can remove filters, not just add them ("remove the salary filter").
