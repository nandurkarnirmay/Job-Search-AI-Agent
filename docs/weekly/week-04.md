# Week 4: Resume analysis, interview practice, application tracker and alert emails (checkpoint: 6 agent tools)

## What we did
The agent now has six career tools: job search, company research, salary research, resume analysis,
interview practice and an application tracker. All of them can be used from the chat, with follow-ups that
refer to earlier results: "how does my resume match the first job?", "save the second job",
"prepare me for the first job", "show my applications".

**Resume analysis.**
- **Upload:** users upload a PDF or DOCX. The file is checked by its contents, not its extension, with limits
  on size, page count and the unpacked size of DOCX files (a zip-bomb guard).
- **Privacy:** the file itself is never stored. We keep the extracted text, with email addresses and phone
  numbers removed, plus the parsed fields.
- **Parsing:** a skills taxonomy of about 150 skills covers software, data, core engineering (SolidWorks, ANSYS,
  GD&T, thermodynamics…) and business. It handles names like C++, C# and .NET. It avoids false matches: "Java"
  inside "JavaScript", "spark plugs", or a "spring internship".
- **Checks:** the parser finds standard section headings and flags problems that hurt ATS screening, such as
  scanned or image PDFs that can't be read, missing contact details, and very short or very long resumes.

**ATS match score.** The 0–100 score is deterministic and explainable:
- **Skills (70 points):** required skills count double and "nice to have" skills count once. Alternatives like
  "Power BI or Tableau" count as one requirement, met by either.
- **Job title (15 points):** how many of the title's meaningful words appear in the resume.
- **Structure (15 points):** standard sections and contact details.

The user sees matched and missing skills plus concrete suggestions. Suggestions always say "if you genuinely
have it", so the tool never encourages claiming skills a candidate doesn't have. A skill-gap review compares
the resume with the skills that current postings for the target role ask for.

**Interview practice.** For a role or a job from the search results, the agent builds a practice set:
- "Tell me about yourself" and "Why this company?"
- up to five technical questions matched to the job's skills (including core mechanical topics)
- two behavioural questions
- one India-specific HR question (notice period, salary expectation in LPA, or relocation)

Each typed answer gets a 1–5 score and specific feedback:
- **Technical answers:** checked against the question's key points.
- **Behavioural answers:** checked for STAR structure, measurable results, and saying "I" rather than "we".
- **HR answers:** must be concrete, e.g. a salary range in LPA with the reasoning behind it.

The score is rule-based and reproducible. The LLM may only add a one-line coaching comment.

**Application tracker.** Jobs can be saved from search results or the chat and moved through Saved → Applied →
Interview → Offer / Rejected / Withdrawn. Each entry keeps a status history, notes and a next-action date. The
same job found on two sites is tracked once. When a job is saved from a search, its details come from our
server-side cache, not from the browser.

**Alert emails.**
- **Scheduling:** the same dispatch function runs from two schedulers. Celery beat runs it hourly in our
  docker-compose setup. A GitHub Actions cron calls a secret-protected endpoint in production, because
  Render's free plan has no background workers.
- **Delivery:** emails go out over SMTP with a one-click unsubscribe link. A job is marked as sent only after
  the email succeeds, so failures are retried instead of lost. Without email configured, results are kept in
  an in-app history.
- **Safety:** a lock prevents double sending.

**Follow-ups can now remove filters:** "remove the salary filter", "any city", "clear filters".

**Testing.** We added about 70 test cases. The resume tests run on a real PDF and real DOCX files. They also
cover ATS grouping and scoring, interview feedback, tracker privacy and duplicates, alert delivery (email
failure retried, sources down, lock, unsubscribe, HTML escaping of third-party job text), the new chat flows,
and migration 0003.

## Contributions
| Member | Work this week |
|---|---|
| Member 1 | Router intents, filter removal, LangGraph tool nodes, chat flows |
| Member 2 | Resume parser, skills taxonomy, ATS scoring, skill-gap review |
| Member 3 | Resume, tracker and interview pages; chat cards; Save button on job cards |
| Member 4 | Interview question bank and feedback, tracker API, alert email dispatch, Celery/cron, tests |

## Challenges and decisions
- **Explainable scores.** We kept ATS and interview scoring rule-based so the same input always gives the
  same score, and every point can be explained. LLM output is limited to optional wording.
- **Honest advice.** Missing-skill suggestions are conditional ("if you genuinely have it") and the skill-gap
  review recommends learning through projects.
- **Privacy.** Resume files are discarded and contact details removed from stored text. Every item is private
  to its owner, and deleting an account deletes the resume, tracker and interview sessions too.
- **Free hosting limits.** Background workers cost money on Render, so production uses GitHub Actions as
  the scheduler. It calls the same function Celery would.

## Checkpoint status
The Week 4 checkpoint asks for an agent with multiple career tools. We have six, all reachable from the chat
with conversation memory.

## Plan for next weeks (Weeks 5–6)
- More data sources with fallbacks, including GitHub profile analysis, to reach the 5+ API requirement.
- Salary benchmarking by experience band, and negotiation tips.
- AI mock interviews with spoken answers (speech-to-text).
- Career-path roadmaps from target role vs current skills.
- Calendar integration for interview dates in the tracker.
