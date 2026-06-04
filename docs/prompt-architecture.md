![banner](../cara-coach-banner.svg)
# Prompt Architecture

Cara Coach makes **6 separate Claude API calls** per session. This document explains what each call does, what goes in, and what comes out.

---

## The 6 calls

| Call | Function | When |
|---|---|---|
| 1 | Gap analysis — CV vs JD | Once per project (cached) |
| 2 | Question generation | Once per project (cached) |
| 3 | CV catalog extraction | Once per project (cached) |
| 4 | Scoring + feedback + ideal answer | Once per answer (6× per session) |
| 5 | Final debrief | Once per session |
| 6 | Follow-up question handler | On demand, when user asks a coaching question |

### Calls per full session (6 questions, no follow-ups)

| Call | Count | Cached? |
|---|---|---|
| Gap analysis | 1× | ✅ After first session |
| Question generation | 1× | ✅ After first session |
| CV catalog extraction | 1× | ✅ After first session |
| Scoring (per answer) | 6× | ❌ Every time |
| Final debrief | 1× | ❌ Every time |
| **Total** | **10×** | **3 cached, 7 fresh** |

The 85% reduction in token usage comes from caching calls 1–3. Once a project is set up, repeat sessions cost only 7 Claude calls instead of 10.

---

## No system prompt

There is no global system prompt. The `system=` parameter is never used in Anthropic API calls — all instructions are embedded directly in the user-role message.

Persona is injected only where needed:

| Call | Persona |
|---|---|
| Scoring | "You are an experienced recruiter and career coach." |
| Follow-up handler | "You are Cara Coach, an AI interview coach." |
| All others | No persona — task instructions only |

---

## What goes into each call

### 1. Gap analysis
```
cv_text           — full CV text
jd_text           — full job description
lang_instruction  — "Respond in English." or "Отвечай на русском языке."
```
Output: a plain-text analysis of gaps between the CV and the JD. This feeds directly into question generation.

---

### 2. Question generation
```
gaps              — output of gap analysis
lang_instruction
+ hardcoded: 6 questions total, 3 domains (Soft / Hard / Behavioural)
```
Output: 6 questions, 2 per domain, grounded in the specific gaps identified.

---

### 3. CV catalog extraction
```
cv_text           — full CV text
jd_text           — full job description
lang_instruction
```
Output: a structured catalog — ROLES / TOP STORIES / KEY METRICS / DOMAINS / STRONGEST MATCH.

This catalog replaces the full CV in all subsequent scoring calls. Sending the full CV every time a question is scored would waste tokens and add noise. The catalog gives Claude exactly what it needs to write grounded ideal answers.

---

### 4. Scoring — the main call

This is the most complex call. It returns everything in a single response — score, feedback, ideal answer, and exec language assessment — to avoid 3 separate API calls per answer.

**What goes in:**
```
question          — the interview question
answer            — candidate's answer (typed or voice transcript)
cv_text           — the CV catalog (not the full CV)
mode              — "coach" or "mirror"
lang_instruction
+ hardcoded: full Executive Language parameter definitions (6 parameters)
```

**What comes out (strict plain-text format):**
```
SCORE:
SUMMARY:
POSITIVE_TITLE:
POSITIVE_BODY:
FLAG_TITLE:
FLAG_BODY:
IMPROVE:
STAR_TIP:
IDEAL:
EXEC_LANG_SCORE:
EXEC_LANG_FEEDBACK:
```

**What doesn't go in:** previous answers, session history, prior scores. Each question is evaluated in isolation.

---

### 5. Final debrief
```
domain_averages   — dict of {domain: avg_score} for the completed session
lang_instruction
```
Output: a 120-word structured debrief — What's Working / Top 3 to Improve / Focus for Next Session.

Note: no individual questions or answers are passed. The debrief is based purely on aggregate scores, not on re-reading the transcript.

---

### 6. Follow-up question handler

The only call that passes real conversational context.

```
interview_question   — the question that was asked
candidate_answer     — the candidate's last answer
feedback_details     — the Details block already shown (if user clicked Details)
ideal_answer         — the Ideal Answer already shown (if user clicked Ideal Answer)
user_question        — what the user just asked
lang_instruction
```

This allows Cara to answer coaching questions in full context — "why did I lose points on structure?" gets a response that references what the user actually said.

---

## The system is stateless between questions

Claude has no memory of question 1 when scoring question 3.

Session context — transcript, scores, patterns — exists in `bot.py` as a Python dictionary, but it's not passed to scoring prompts. The exception is the follow-up handler, which gets the context for the current question only.

```
sessions[chat_id] = {
    "transcript_lines":  [...],  # in memory
    "question_scores":   [...],  # in memory
    "domain_scores":     {...},  # in memory
    "exec_lang_scores":  [...],  # in memory
    # none of this reaches the scoring prompt
}
```

This is a deliberate tradeoff. Passing full session history to every scoring call would increase cost and latency significantly. The current approach scores each answer on its own merits — which is arguably closer to how a real interviewer evaluates answers anyway.

Cross-session pattern analysis happens outside Claude, in the web dashboard and via `.md` export.

---

## Known limitations

**Stateless scoring** means Cara can't notice improvement within a session — if answer 6 is much better than answer 1, the scores reflect each answer independently but there's no "you've improved" signal mid-session. This is on the post-MVP roadmap.

**Final debrief without transcript** means the debrief is based on numbers, not on re-reading what was actually said. This keeps cost low but limits the depth of the closing analysis.

---

## Output parsing and failure modes

The scoring call returns a strict plain-text format with labelled fields (`SCORE:`, `SUMMARY:`, `IDEAL:`, etc.). The parser extracts each field by looking for the exact prefix at the start of a line.

**There is no retry logic.** One call, one result — whatever comes back gets parsed.

### What happens when a field is missing or malformed

**SCORE** — the most critical field. Two extraction attempts:
1. Direct integer parse
2. Regex fallback — looks for any number 1–10 in the string

If both fail, `score_num = None`. The question silently drops out of session statistics. No error is shown to the user — the session continues as if nothing happened. In the final summary and `.md` export, that question simply doesn't appear.

**Most other fields** (SUMMARY, POSITIVE, FLAG, IMPROVE, STAR_TIP) — if empty, the corresponding section renders with a header but no body. Visually awkward but not broken.

**IDEAL** — the one field with an explicit fallback: if empty, the user sees `"⚠️ Ideal answer wasn't generated for this question. Try again ↓"`. This is the only user-facing error message in the parsing layer.

**EXEC_LANG_SCORE** — if missing or unparseable, it's silently omitted from the score card and session averages.

**Question generation** — if Claude doesn't follow the domain format and all three domain lists come back empty, the session immediately jumps to completion with zero questions asked. This is the most disruptive failure mode in the system.

### Why this matters

The parser is sensitive to markdown formatting. If Claude returns `**7**` instead of `7`, or `**SCORE:**` instead of `SCORE:`, the field won't be found. In practice this is rare — the prompt is explicit about plain-text output — but it's not impossible, especially at high load or with model updates.

### What's planned

Explicit format validation before parsing, retry on malformed response (max 1 retry), and a visible warning to the user when a score couldn't be extracted. These are post-MVP improvements — the current behaviour is acceptable for single-user MVP use but would need hardening before a multi-user production release.

---

*Part of Cara Coach product documentation. See also: [Feature Inventory](./feature-inventory.md) · [Executive Language Scoring](./executive-language-scoring.md) · [Product Brief](./product-brief.md)*
