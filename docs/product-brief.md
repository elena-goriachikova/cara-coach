![banner](../cara-coach-banner.svg)

##  Product Brief v2.0

**AI-Powered Interview Preparation Agent**

Elena Goriachikova · June 2026 · Confidential

##  **01 Overview**

Cara Coach is an AI-powered interview preparation agent that simulates
real job interviews and delivers structured, personalised feedback. It
runs as a Telegram bot with a web dashboard for session management and
analytics.

Unlike generic interview tools, Cara grounds every question in the
user\'s actual CV and job description - making each session feel like
a real interview with a hiring manager who has read your background.

**Status:** Active development - functional MVP

**Platform:** Telegram Bot + Flask Web Dashboard

**Tech stack:** Python · Claude API (Anthropic) · OpenAI Whisper ·
SQLite · Flask

**Languages:** English · Russian (multilingual architecture)

**Author:** Elena Goriachikova, Senior PM/BA → AI Agent Strategist

##  **02 Problem**

Senior professionals preparing for AI-strategy interviews face a
specific gap: existing tools give generic feedback, not personalised
coaching grounded in their actual experience.

**What\'s missing in the market**

> **→** Questions not grounded in the candidate\'s real CV - generic
> templates instead of personalised scenarios
>
> **→** No executive language feedback - tools score content but
> ignore how you sound as a leader
>
> **→** No speech analysis - filler words, pace, answer length go
> undetected
>
> **→** No structured improvement loop - one-shot feedback with no
> retry mechanism
>
> **→** No session analytics - no way to track progress over time or
> identify patterns

##  **03 Solution**

Cara Coach solves this by combining three layers of intelligence:

> **→** CV-grounded personalisation - questions and ideal answers
> built from the user\'s real projects and experience
>
> **→** Executive Language scoring - 6-parameter assessment of how
> senior and confident the user sounds, independent of content
>
> **→** Structured feedback loop - Score → Details → Ideal Answer →
> Retry, with analytics across sessions

The result: preparation that feels like a real interview, not a quiz.
The user practices under realistic conditions, gets honest feedback, and
improves measurably over time.

##  **04 Target Users**

**Primary (MVP)**

> **→** Senior PMs, BAs, and product leaders preparing for AI-strategy
> or agent-strategy interviews
>
> **→** Professionals targeting roles at AI-native companies where both
> technical depth and executive communication are evaluated
>
> **→** Non-native English speakers who need extra practice with
> professional vocabulary and executive register

**Secondary (Post-MVP with auth + hosting)**

> **→** Any professional preparing for senior-level interviews across
> industries
>
> **→** Executive coaches who want a structured tool for their clients

Note: MVP is single-user (no auth). Multi-user architecture is designed
and ready - requires hosting and authentication layer to activate.

##  **05 Core Features - MVP**

**Telegram Bot**

> **→** Multi-vacancy selection - user picks which job to practise for
>
> **→** CV-grounded questions across 3 domains: Soft Skills / Hard
> Skills / Behavioural
>
> **→** Voice input via OpenAI Whisper - full flow from speech to
> scored feedback in \~13 seconds
>
> **→** Text input - typed answers evaluated identically to voice
>
> **→** Streaming score delivery - user sees feedback building in real
> time
>
> **→** Progressive disclosure: Score → Details → Ideal Answer → Retry
>
> **→** Dynamic button hiding - used buttons disappear, reset on retry
>
> **→** Follow-up questions in context - user can ask coaching
> questions after any answer
>
> **→** Score delta on retry - shows +2 / -1 / no change vs previous
> attempt
>
> **→** Session completion with per-domain scores, strongest/weakest
> question, final debrief
>
> **→** Auto-generated .md transcript at session end

**Executive Language Scoring**

Applied to every answer regardless of domain. Composite score 1--10
based on 6 parameters:
| Parameter | What it measures | Question-aware |
|---|---|---|
| Top-down structure | Main point first | Always applied |
| Hedging density | Frequency of 'I think / maybe / I guess' | Always |
| Apology language | Frequency of 'Sorry if this is long' | Always |
| Result presence | Is there a measurable outcome? | Only when relevant |
| Professional

Feedback delivered as verbatim quotes from the user\'s answer with
rewrites in senior executive register: \"You said: \[quote\] → Try
instead: \[rewrite\]\"

**Web Dashboard**

> **→** Project creation and editing - role, company, JD, language,
> mode, date
>
> **→** CV upload - .txt and .docx supported
>
> **→** Vacancy sidebar sorted by last session date
>
> **→** Session statistics: count, last score with delta, best, average,
> exec language average
>
> **→** Progress bars per category (Soft / Hard / Behavioural / Exec
> Lang)
>
> **→** Sessions table: Date · Overall · Soft · Hard · Behavioural ·
> Exec Lang · Retried · Export
>
> **→** Per-session .md export download
>
> **→** Date range export - all sessions in a period as one combined
> .md file
>
> **→** Close / Reopen vacancy - session history preserved on close

**Speech Analysis**

> **→** Pace analysis - flags too slow (\<90wpm) or too fast
> (\>160wpm)
>
> **→** Answer length analysis - too short (\<30s), optimal, or too
> long (\>120s)
>
> **→** Filler word detection - 18-word list in English and Russian

Note: analysis is text-based (works on both typed and transcribed
answers). Duration/pace estimated from word count.

**Performance & Architecture**

> **→** Smart cache invalidation - cache cleared only when JD or CV
> actually changes, not on every save
>
> **→** 85% reduction in Claude API calls via CV story catalog caching
> and merged score+ideal answer calls
>
> **→** Streaming responses via AsyncAnthropic - no silent waits
>
> **→** Session persistence to disk - survives bot restart
>
> **→** Multi-chat support - session isolation by chat_id
>
> **→** API keys via macOS Keychain - no .env file, secrets never in
> code

##  **06 Feedback Modes**

| | COACH | MIRROR |
|---|---|---|
| **Tone** | Honest but supportive. Highlights strengths, then improvement areas. Warm but direct. | Direct and uncompromising. No softening. Names weaknesses plainly. |
| **Best for** | Early preparation, building confid

Mode is set once per project in the web dashboard and applies to all
sessions for that vacancy.

##  **07 CV Personalisation Engine**

At session start, Cara runs a one-time analysis that extracts a
structured CV catalog from the user\'s CV:

> **→** ROLES - job titles and companies held
>
> **→** TOP STORIES - 5--7 high-impact project narratives
>
> **→** KEY METRICS - quantified outcomes (team sizes, % improvements,
> revenue figures)
>
> **→** DOMAINS - industries and functional areas covered
>
> **→** STRONGEST MATCH - best-fit experience for the target JD

This catalog powers two things:

> **→** Questions are contextualised: \"You led a team of 110 at BT
> Group - how did you manage transparent communication at that
> scale?\"
>
> **→** Ideal answers are grounded in real experience: Claude writes a
> model answer using ONLY the user\'s actual projects. It does not
> invent experience at the target company.

The catalog is cached and reused across sessions. It is only regenerated
if the CV or JD actually changes - not on every save.

##  **08 Session Flow**
| # | Step | Detail |
|---|------|--------|
| 1 | **Setup** | User creates vacancy in web dashboard: uploads CV, pastes JD, selects language and feedback mode |
| 2 | **Start** | User sends /start in Telegram. Bot checks cache — instant start if cached, or runs 3-step analysis (CV gaps → questions → CV catalog) |
| 3 | **Question delivery** | Questions delivered with domain announcement and progress counter. 6 questions total: 2 Soft / 2 Hard / 2 Behavioural |
| 4 | **Answer** | User answers by voice (Whisper transcription) or text. SKIP available at any point |
| 5 | **Score card** | Streaming feedback: Score + Executive Language score. Summary visible immedi

##  **09 Post-MVP Roadmap**

**Authentication & Hosting**

> **→** User auth (signup/login) - UI stubs already exist in frontend
>
> **→** Cloud hosting (Railway / Render) - enables multi-user access
>
> **→** Per-user CV storage - remove global my_cv.txt constraint

**Configurable Parameters**

> **→** Question count - currently hardcoded at 6 (2 per domain)
>
> **→** Session window - currently hardcoded at 24h display
>
> **→** Estimated time - currently hardcoded at \~30 min
>
> **→** Real-time dashboard refresh - currently manual reload

**PDF Support**

> **→** PDF CV parsing - currently broken (saves raw bytes). Needs
> PyPDF2 or pdfminer

**Analytics & Intelligence**

> **→** Pattern analysis across sessions - 80/20 of recurring mistakes
>
> **→** Progress tracking over time with trend lines
>
> **→** Suggested focus areas based on session history

##  **10 Technical Architecture**

| Layer | Technology | Purpose |
|---|---|---|
| **AI — scoring & feedback** | Claude API (Anthropic) claude-haiku-4-5 | Question generation, gap analysis, scoring, ideal answers, exec language, final debrief |
| **AI — voice** | OpenAI Whisper-1 | Speech-to-text transcription (EN + RU) |
| **Bot framework** | python-telegram-bot (async) | Telegram interface, button handling, streaming |
| **Web backend** | Flask (Python) | Project management API, session data, export endpoints |
| **Storage** | SQLite (file-based) | Session history, project settings, cached analysis |
| **CV parsing** | python-docx | .docx → plain text extraction |
| **Security** | macOS Keychain | API keys stored securely, never in code or .env |
| **Export** | Markdown (.md) | Session transcripts — lightweight, readable, LLM-ready |


##  **11 Success Metrics**

Cara Coach measures improvement across three layers: behavioural change,
quantitative score trends, and real-world outcome.

**Quantitative - tracked automatically per session**

| Metric | What it measures | Success signal |
|---|---|---|
| **Overall score trend** | Average score across sessions for the same vacancy | Upward trajectory over 3+ sessions |
| **Executive Language trend** | Composite exec lang score per session | Score increases; hedging density decreases |
| **Retry rate** | How often user retries per session | Decreasing over time — gets it right first time |
| **Filler word count** | Frequency of uncertainty markers per answer | Fewer fillers in later sessions |
| **Response fluency** | Word count stable or growing while score improves | Same content delivered faster and cleaner |
| **Top-down structure adoption** | Main point first vs buried in answer | Positive signal rate increases in Details feedback |


**Qualitative - behavioural improvements**

> **→** Answers become more specific - fewer generic statements, more
> concrete cases with metrics and outcomes
>
> **→** Top-down structure adopted - main point delivered first,
> details follow
>
> **→** Professional vocabulary improves - domain terms used naturally
> without prompting
>
> **→** Fluency under pressure - user orients faster, answers feel
> less like searching for words

**Proxy metric - real-world outcome**

> **→** Interview conversion rate - user receives interview invitation
> or offer after preparing with Cara

This is the strongest signal but requires voluntary user follow-up. To
be tracked post-MVP via optional session tagging (\'Got the offer\').

##  **12 Competitive Landscape**

The AI interview preparation market is growing rapidly. Most tools focus
on question generation and generic content feedback. Cara Coach occupies
a differentiated position: executive-level coaching grounded in the
user\'s real experience.

| Feature | Cara Coach | Final Round AI | Richard McMunn | Sensei AI | Generic ChatGPT |
|---|---|---|---|---|---|
| **CV-grounded questions** | ✅ Yes | ⚠️ Partial | ✅ Yes | ❌ No | ❌ No |
| **Ideal answer from real CV** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Executive Language scoring** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Speech / filler analysis** | ✅ Yes | ⚠️ Partial | ❌ No | ⚠️ Partial | ❌ No |
| **Session analytics & trends** | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Voice input (mobile)** | ✅ Telegram | ⚠️ Web only | ❌ No | ✅ Yes | ❌ No |
| **Retry with score delta** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Works on phone, any time** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Multi-vacancy management** | ✅ Yes | ⚠️ Partial | ❌ No | ❌ No | ❌ No |
| **Export + pattern analysis** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |

Key differentiator: Cara is the only tool that combines CV-grounded
personalisation, Executive Language scoring, voice input on mobile,
session analytics, and export for external pattern analysis - in one
product.

##  **13 Vision**

Cara Coach starts as an interview preparation tool. The longer arc is
bigger.

**Where we are now - MVP**

> **→** Single user, local deployment, Telegram + web dashboard
>
> **→** Preparation for a specific vacancy with structured feedback and
> session analytics

**12 months - Multi-user platform**

> **→** Authentication + cloud hosting - any professional can sign up
> and use Cara
>
> **→** Cross-session intelligence - Cara identifies your recurring
> patterns and suggests what to practise next
>
> **→** Configurable parameters - question count, session length,
> domain weighting
>
> **→** Progress reports - weekly digest of improvement areas sent
> automatically

**24 months - Adaptive coaching agent**

> **→** Cara remembers your history across all vacancies and builds a
> personal development model
>
> **→** Proactive coaching - \'You\'re applying to Sierra next week.
> Based on your last 6 sessions, focus on top-down structure and result
> presence\'
>
> **→** Team version - managers use Cara to prepare their reports for
> promotion interviews or board presentations
>
> **→** Integration with job search tools - Cara knows which role
> you\'re targeting and adjusts coaching accordingly

**The vision: an agent that knows your career better than you do - and
prepares you for what\'s next before you ask.**

*Part of Cara Coach product documentation. See also: [Feature Inventory](./feature-inventory.md) · [Executive Language Scoring](./executive-language-scoring.md) · [Product Brief](./product-brief.md)*


**Preparation that actually moves the needle.**

![footer](../cara-coach-int-footer.svg)

