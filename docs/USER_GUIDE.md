# User guide

## 1. Get started (2 minutes)
1. **Sign up** with email and a password of 8+ characters.
2. **Profile**: add your city, experience, skills, expected salary (LPA), notice period, target roles and, if you
   have one, your GitHub username. Searches and the career roadmap use these as defaults.
3. **Resume**: upload a PDF or DOCX. The file is read and thrown away; we keep the text with your email and phone
   removed, encrypted.

> The free server sleeps when unused. If the first page says "can't reach the server", wait 30–60 seconds and retry.

## 2. Ask the assistant (Search page)
Type what you'd say to a friend. Examples:
| You type | What happens |
|---|---|
| `remote python jobs in Bengaluru above 8 LPA for a fresher` | search with all filters |
| `what about Pune?` · `only hybrid` · `remove the salary filter` | changes the last search |
| `tell me about the second company` | company overview + its openings and salaries |
| `salary for data analyst in Hyderabad with 3 years` | percentiles, by experience band |
| `how does my resume match the first job?` | ATS score with missing skills |
| `save the second job` · `show my applications` | tracker |
| `prepare me for the first job` | mock interview set |
| `I got an offer of 7.5 LPA for data analyst in Pune, is it fair?` | negotiation advice and an email draft |
| `roadmap to become a data engineer` | skills plan in 6-week phases |
| `review my github` · `analyse github torvalds` | GitHub profile check |

Every number shows its sample size. "Not enough data" means fewer than 3 data points; we don't guess.
"Results may be out of date" means all job sites were down and you're seeing the last good results.

## 3. Career page
- **Roadmap**: pick a role; skills you already have are ticked. Mark skills *learning* or *done* and the roadmap
  recalculates. Resources are official docs or free courses (NPTEL for core engineering).
- **Salary**: benchmark by city and experience, with a chart per experience band.
- **Negotiate**: enter the offer (and current/competing CTC if any). You get a verdict, a counter-offer, the
  reasoning, an email you can copy, and a checklist of CTC components to ask about (fixed vs variable, joining
  bonus, notice buy-out…). The counter is a starting point, not a guarantee.
- **GitHub**: what your public repos prove, skills on GitHub missing from your resume, and resume skills with no
  public evidence.

## 4. Interview practice
1. Interview → enter a role (or start from a job in chat).
2. For each question choose **Type** or **Speak** (Chrome, Edge or Safari; allow the microphone). Speak as in the
   interview, then press **Stop & get feedback**.
3. Feedback: score 1–5, what you covered and missed, tips, and for spoken answers your pace (aim 110–160
   words/min), filler words and long pauses.
4. If an answer skips something (your own action, a result, a key point), a **follow-up** question appears under it,
   like a real interviewer would ask.
5. **Session report** summarises your averages, weakest answers and what to practise next.

We never receive audio, only the transcript and timing. Transcription is done by your browser's speech service,
which may send the audio to the browser vendor (Google for Chrome, Apple for Safari). If that's a problem, type.

## 5. Tracker and calendar
- Save jobs from search, move them Saved → Applied → Interview → Offer / Rejected / Withdrawn, add notes and a
  next-action date.
- **Calendar** (Tracker page): add interviews, follow-ups and deadlines, linked to an application. Each has
  "Add to Google Calendar" and a `.ics` download (Outlook, Apple). Reminders by email 1 day and 1 hour before,
  if email is configured.
- **Subscribe**: create a private feed URL and paste it into Google Calendar → Other calendars → From URL. Anyone
  with the URL can see your events: rotate it if you shared it by mistake.

## 6. Alerts
Create from any search; daily or weekly. Only jobs you haven't been sent before count. Every email has a one-click
unsubscribe. History shows each run.

## 7. Dashboard
Your funnel (tracked → applied → interview → offer), activity per week, practice scores over time, upcoming events.

## 8. Privacy (Settings)
- **Download my data**: everything we store about you, as JSON.
- **Delete account**: removes everything immediately and permanently.
- Old conversations (> 180 days idle) are deleted automatically.
Details: [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md).

## Limits
- Job data comes from Adzuna, JSearch and Jooble; we don't scrape Naukri/LinkedIn. Coverage varies by city and role.
- No company reviews or ratings: there's no public API, and we won't invent them.
- Salary data is only as good as what listings disclose; many Indian listings don't.
