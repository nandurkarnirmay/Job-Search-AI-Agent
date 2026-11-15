# Building a job-search agent for India where the LLM isn't allowed to do maths

*Draft for the final submission. Add team names, the live link and 2–3 screenshots before publishing (Medium /
Hashnode / dev.to).*

Most "AI job assistants" are a chat box around a language model. Ask one what a data analyst earns in Pune and it
answers confidently with a number it can't source. For a job seeker deciding whether to accept 6.5 LPA, a fluent
wrong number is worse than no number. That constraint shaped everything we built in eight weeks.

## The rule: numbers come from code
Our agent (FastAPI + LangGraph) routes each message to one of 13 tools: job search, company research, salary, resume
ATS match, interview practice, tracker, negotiation, career roadmap, GitHub review and a few more. The tools compute;
the language model (Gemini) only does what models are good at: understanding messy phrasing and rewording.

- **Salaries** are percentiles over salaries disclosed in live listings, grouped by experience band, always with the
  sample size. Fewer than 3 data points → "not enough data", never a guess.
- **Negotiation** places the offer within that band and applies a written rule (below the 25th percentile → counter
  at the median; and so on), capped at +25 % unless you hold a higher competing offer. Every line of advice can be
  traced to a number.
- **Company research** paraphrases Wikipedia, and any paraphrase that introduces a number not in the source is
  thrown away.

## Rules first, model second
Calling an LLM for every message is slow, costs money and is unpredictable. Our router is regex rules for the cases
we can recognise ("what about Pune?", "save the second job", "is 7.5 LPA a fair offer"), which cost 0.1 ms. Only
messages no rule matches go to Gemini, and its answer is checked: it can't send you to research a company you never
named. On our 64-message test set the rules alone route every message correctly. We report the honest number too:
on first contact with the test set they got 95 %, and we fixed the misses.

## Indian specifics are the product
LPA salaries written six different ways ("₹25,000 a month", "6L–9L p.a."), notice periods, CTC components
(fixed vs variable, joining bonus, notice buy-out), and core-engineering roles that generic tools ignore: our skills
taxonomy knows SolidWorks, ANSYS and GD&T, and roadmaps point mechanical engineers to NPTEL, not React tutorials.

## When every job site is down
Three tiers: two primary sources in parallel, a third (Jooble) only if they fail or return fewer than 10 jobs, and
finally the last good result from cache, clearly labelled "may be out of date". Each client has retries with
backoff, a throttle and a circuit breaker.

## Mock interviews that ask "and what did *you* do?"
You answer by voice in the browser. Scoring is rule-based and reproducible: key points covered, STAR structure,
measurable results, pace (110–160 words/min), fillers per 100 words. If you say "we built the dashboard", the
interviewer follows up asking what *your* part was, the way a real one would.

## Privacy by default
Resume files are read and discarded; chat, resume text, notes and answers are encrypted per field; old
conversations expire; you can download or delete everything. Our server never receives audio. We were explicit about
what we *didn't* solve (token storage, shared database) in a written security assessment.

## What we'd do differently
- Build the held-out evaluation set on day one, written by people outside the team.
- Start with one service; we split into four for the brief, and free-tier cold starts made that the slowest part of
  the demo.
- Fewer features, deeper: our salary data is only as good as what Indian listings disclose, and many don't.

*Code: <GitHub link> · Live: <Vercel link> · Demo video: <link>*
