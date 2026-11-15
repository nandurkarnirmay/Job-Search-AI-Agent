# Week 6: Voice mock interviews, calendar integration, accuracy evaluation (checkpoint: specialised features)

## What we did
**AI mock interviews v2.**
- **Voice answers:** users speak their answers in the browser using the Web Speech API with Indian English.
- **Privacy:** our server receives only the transcript and timing, never audio. The UI states that the browser's
  speech service (Google in Chrome) processes the audio.
- **Spoken-answer feedback:** pace (target 110–160 words/min), filler words per 100 words ("um", "basically",
  "actually", "like") and long pauses, on top of the Week 4 content scoring.
- **Follow-up questions:** when an answer misses a key point, says "we" instead of "I", gives no measurable result,
  or leaves a technical choice unjustified, the interviewer asks a follow-up under that question.
  - The LLM may word the follow-up, with a guard. Otherwise a rule-based follow-up is used.
  - At most one follow-up per question.
- **Session report:** averages by question type, the weakest answers, average pace, recurring tips and next steps.

**Calendar integration.**
- **Events:** interviews, follow-ups and deadlines, optionally linked to a tracked application.
- **Export:** each event has an "Add to Google Calendar" link and a standard `.ics` file for Outlook and Apple, with
  reminders 1 day and 1 hour before.
- **Private feed URL:** Google or Outlook can subscribe to a feed URL that is random, rotatable and revocable. It
  also includes the tracker's next-action dates.
- **Email reminders:** sent from the same scheduler as job alerts and marked sent only after success.
  Rescheduling an event re-arms its reminder.
- **No OAuth:** this works for every calendar app with no Google verification process.

**Accuracy evaluation.** We labelled 64 chat messages across 13 intents and 25 resume/job snippets for skill
extraction (`python -m scripts.eval_accuracy`).

| Measure | First run | After fixes |
|---|---|---|
| Router accuracy | 61/64 (95.3 %) | 64/64 |
| Skill extraction F1 | 0.975 | 0.994 |

We fixed the causes in the code, not the labels. Examples: offers phrased as questions, filler-only follow-ups,
"Spring" vs "Spring Boot".

**Testing.** We added tests for:
- negotiation scenarios: below, around and above market, and with a competing offer
- salary bands and the Indian salary parser
- Jooble fallback triggers and the stale-cache tier
- the GitHub report (with a fake GitHub client), roadmap recalculation
- iCalendar format: escaping, line folding, alarms
- reminder dispatch
- spoken-answer metrics and follow-ups
- migration 0004

## Contributions
| Member | Work this week |
|---|---|
| Member 1 | Follow-up question logic (LLM with guard + rules), session report, interview router |
| Member 2 | Evaluation sets and script, router/skills fixes from the evaluation |
| Member 3 | Voice input, interview page (follow-ups, metrics, report), calendar panel in the tracker |
| Member 4 | Calendar API, .ics generator, feed, email reminders, tests |

## Challenges and decisions
- **Speech-to-text.** A server-side model (Whisper) costs money and would mean storing audio. Browser speech
  recognition is free and keeps audio off our server. The trade-offs: it doesn't work in Firefox, and Chrome sends
  audio to Google. We state both in the UI and keep typing as the alternative.
- **Calendar without OAuth.** The Google Calendar API needs app verification for sensitive scopes. ICS files plus a
  subscribable feed cover Google, Outlook and Apple with no verification. The feed URL is a secret, so it can be
  rotated or revoked.
- **Honest accuracy.** Our test set is small and we fixed what it found, so we report the first-run numbers as
  the real estimate.

## Checkpoint status
The Week 6 checkpoint asks for specialised career features, integrated and tested. Mock interviews (voice and
follow-ups), salary benchmarking and negotiation, career roadmaps and calendar integration are all available in
the chat and the UI. Each has automated tests, plus an accuracy evaluation for routing and skills.

## Plan for next week
Analytics dashboard, splitting into services, encryption at rest, security assessment, API docs and user guide.
