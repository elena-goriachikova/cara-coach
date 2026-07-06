![banner](./cara-coach-banner.svg)

##  AI-powered interview preparation agent. Built by a product manager, for professionals.

<img src="https://img.shields.io/badge/What%20is%20this-00897B?style=for-the-badge&logoColor=white"/>

Cara Coach is a conversational AI agent that simulates real job interviews and gives structured, personalised feedback on your answers.

You upload your CV and the job description. Cara reads your experience and builds a question set grounded in your actual projects — not generic templates.
Then the interview starts. Cara asks. You answer. She listens like a real interviewer would — checking not just what you know, but how you communicate it: hard skills, soft skills, behavioural answers, and executive language.
She also notices what most people miss: whether your answer ran too long, whether your structure was clear, whether filler words crept in. The things that cost you the job even when you knew the answer.
After each response you get structured feedback: **what landed, what to sharpen, and a score out of 10**.

It runs on Telegram (your phone, any time) and has a web dashboard for tracking progress over time.

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>

<img src="https://img.shields.io/badge/Why%20I%20built%20it-00897B?style=for-the-badge"/>

I was preparing for senior AI-strategy interviews and couldn't find a tool that gave honest, structured feedback — not just generic encouragement. And nothing personalised questions to *my* experience.

So I built one. It also happens to demonstrate exactly the skills I'm interviewing for: AI agent design, conversation architecture, product thinking, and Python development.

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>

<img src="https://img.shields.io/badge/How%20it%20works-00897B?style=for-the-badge"/>

**Step 1 — Setup (web dashboard)**
Upload your CV and the job description. The system parses your CV into a structured profile: projects, roles, team sizes, outcomes, domain expertise. This becomes the foundation for everything that follows.

**Step 2 — Practice (Telegram bot)**
Start a session. Cara asks you interview questions — not generic ones, but questions grounded in your actual experience. For example:

> *"You led a team of 110 at BT Group — how did you manage transparent communication at that scale?"*

**Step 3 — Review (web dashboard)**
After each session, review your scores across four dimensions. Export the transcript. Analyse patterns. Come back and go again.

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>


<img src="https://img.shields.io/badge/Features-00897B?style=for-the-badge"/>


<img src="https://img.shields.io/badge/Telegram%20bot-00897B?style=for-the-badge"/>

**Smart button logic: Details → Ideal Answer → Retry**

Buttons appear in sequence and hide after use — by design.

- **Details** appears first: gives hints and directional feedback before revealing the answer. The goal is to make the user think, not copy.
- **Ideal Answer** appears only after Details: shows a model answer built from the user's *own projects and experience* — not a generic template. If the user's CV doesn't contain a direct example, the system infers the best-fit project based on secondary signals (industry, team size, role, outcomes).
- **Retry** — after reading feedback, the user can re-record their answer immediately, while the insight is fresh. Retry count is tracked separately so it doesn't inflate the base score. Working on mistakes while memory is hot is how learning actually sticks.
- Buttons reset on the next question — a clean slate every time.

**Auto-generated `.md` transcript after every session**

Format chosen deliberately: `.md` is lightweight, readable on a large monitor for end-of-day review, and — critically — it's a direct input for the next step. Feed the transcript to a chat model, ask it to identify patterns and the 80/20 of recurring mistakes. PDF would waste tokens. `.md` is enough.

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>


<img src="https://img.shields.io/badge/Web%20dashboard-00897B?style=for-the-badge"/>

**Four-dimension scoring: Soft / Hard / Behavioural / Executive Language**

Not one overall score — four separate dimensions, because they develop at different rates and require different interventions:

- **Hard skills** — domain knowledge. Fastest to improve.
- **Soft skills** — communication, empathy, stakeholder management. Takes longer, requires deliberate practice.
- **Behavioural (STAR format)** — a separate skill from knowing the answer. Many strong candidates fail here simply because they can't structure a story under pressure.
- **Executive Language** — how you sound, independent of what you say. Added after recognising this was a missing dimension in all existing tools.

**Executive Language Score — 6 parameters**

Evaluated on every question, regardless of category:

| Parameter | Logic |
|---|---|
| Top-Down Structure | Main point first, details after. Burying the conclusion is penalised. |
| Hedging Density | Frequency of uncertainty markers (*I think, maybe, I guess, hopefully*) relative to answer length. |
| Apology Language Density | Frequency of apology phrases (*sorry if this is long, I hope that makes sense*) relative to answer length. |
| Result Presence | Is there a result — qualitative or quantitative? Applied only when the question implies one. |
| Professional Vocabulary | Domain-appropriate language, not layperson explanation. |
| Pattern & Framework Thinking | Does the answer reflect a method, or just retell one case? Applied only when the question is about process or approach. |

Feedback delivered in the **Details block** — tone adapted to session mode (MIRROR: direct / COACH: warmer). Ideal Answer is not touched — it's already written at the right executive level and serves as a live example.

**Session table with Export**

Columns: Date · Overall · Soft · Hard · Behavioural · Exec Language · Retried · Export

- **Retried** shows real retry count per session — separate from base scores
- **Export** downloads the `.md` transcript for that session
- **Date range export** — download all sessions in a period as one combined file, ready for pattern analysis

**Vacancy management: open / close / reopen**

Closing a vacancy does not delete session history. All previous sessions are preserved and statistics accumulate when the vacancy is reopened. Because job searches are non-linear — you pause, you revisit, you continue.

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>


<img src="https://img.shields.io/badge/Infrastructure-00897B?style=for-the-badge"/>


**Smart cache invalidation**

Discovered during first testing: re-parsing the CV and JD on every session was burning tokens on static data. CV and job description don't change between sessions — only the answers do. After measuring token consumption and restructuring the cache, token usage dropped by **85%**. Cache now invalidates only when the CV or JD actually changes.

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>

<img src="https://img.shields.io/badge/Tech%20stack-00897B?style=for-the-badge"/>

| Layer | Tech |
|---|---|
| Language | Python 3.11 |
| AI | Claude API (Anthropic) |
| Bot | python-telegram-bot |
| Web | Flask + HTML/CSS |
| Storage | SQLite |
| Export | Markdown (.md) |
| Interview language | English · French · German · Russian |


<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>


<img src="https://img.shields.io/badge/How%20to%20run-00897B?style=for-the-badge"/>

```bash
git clone https://github.com/YOUR_USERNAME/cara-coach
cd cara-coach
pip install -r requirements.txt

# Add your keys to .env
ANTHROPIC_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token

python bot.py        # Telegram bot
python app.py        # Web dashboard → localhost:5000
```

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>


<img src="https://img.shields.io/badge/Project%20structure-00897B?style=for-the-badge"/>


```
cara-coach/
├── bot.py              # Telegram bot logic
├── app.py              # Flask web app
├── agent.py            # Claude API integration
├── db.py               # SQLite operations
├── templates/          # Web dashboard HTML
├── sessions/           # Auto-saved .md transcripts
└── settings.json       # Vacancy config & status
```

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>

<img src="https://img.shields.io/badge/Background-00897B?style=for-the-badge"/>

Built as part of a structured self-study programme in AI agent development.
Product brief, state diagram, edge cases document, and system prompt architecture available on request.

<img width="100%" height="2" src="https://img.shields.io/badge/--%20-E0F2F1?style=flat&labelColor=E0F2F1&color=E0F2F1"/>


<img src="https://img.shields.io/badge/About%20the%20author-00897B?style=for-the-badge"/>


Senior PM/Lead BA with 20+ years in enterprise (BT Group, Primark, Janssen, AIB, Henry Schein).
Currently focused on AI agent strategy and agentic product design.

[LinkedIn →](https://www.linkedin.com/in/elena-goriachikova-4a6b8b4/)

## Related work

- [Sweepster](https://github.com/elena-goriachikova/sweepster) — explainable GenAI career intelligence and vacancy matching architecture.

![footer](./cara-coach-footer.svg)
