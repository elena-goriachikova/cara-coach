![banner](../cara-coach-banner.svg)

# Executive Language Scoring

## What is it?

Executive Language Score is a separate scoring dimension in Cara Coach that evaluates **how** you sound — independent of **what** you say.

A candidate can give a technically correct answer and still sound junior. Executive Language scoring catches exactly that gap: the hedging, the apology language, the buried conclusions, the generic vocabulary that signals uncertainty rather than authority.

It applies to **every answer in every session**, regardless of domain (Soft Skills, Hard Skills, or Behavioural).

---

## Why it matters

Most interview preparation tools score content. They check whether you covered the right points.

None of them score register — the executive communication style that separates a strong senior candidate from a great one.

In reality, hiring managers at senior level evaluate both simultaneously:
- **What** you know (content score)
- **How** you carry yourself (executive language score)

Cara Coach is the only tool that measures both.

---

## The 6 Parameters

### 1. Top-Down Structure
**Always applied.**

Does the answer lead with the main point, or does it arrive at the conclusion after a long build-up?

Senior communicators state the point first, then support it with detail. Junior communicators often tell the story chronologically and arrive at the conclusion at the end — which buries the most important information.

> ❌ "So we had this situation where... and then we tried... and eventually the outcome was good."
> ✅ "We increased retention by 23%. Here's how we got there."

---

### 2. Hedging Density
**Always applied.**

How frequently does the answer contain uncertainty markers relative to its length?

Hedging words signal lack of confidence and undermine authority even when the content is strong.

**Flagged words (English):** I think, maybe, sort of, kind of, I guess, probably, hopefully, I believe, I suppose, perhaps, somewhat, fairly, rather, quite, I feel like

**Scoring logic:**
- One hedge in a long answer → acceptable
- High density → penalised

---

### 3. Apology Language Density
**Always applied.**

How frequently does the answer contain apology phrases?

Apology language is a common pattern among non-native speakers and candidates who feel uncertain. It signals low confidence and wastes valuable interview time.

**Flagged phrases:** Sorry if this is long, I don't know if I'm answering correctly, I hope that makes sense, I'm not sure if this is what you're looking for, Apologies if this isn't relevant, I might be wrong but

**Scoring logic:** Same as hedging — frequency relative to answer length.

---

### 4. Result Presence
**Question-aware — only applied when the question implies a result.**

Does the answer include a concrete outcome — qualitative or quantitative?

Senior candidates quantify impact. Junior candidates describe activity.

> ❌ "I worked with the team to improve the process."
> ✅ "We reduced onboarding time from 6 weeks to 3, which freed up 2 FTEs for new projects."

**Both qualitative and quantitative results are accepted.** Not every outcome can be measured in numbers — "significantly improved stakeholder trust" is a valid result if it's specific.

**If the question doesn't imply a result** (e.g. "How do you approach stakeholder management?") — this parameter is not applied. No unfair penalty.

---

### 5. Professional Vocabulary
**Always applied.**

Does the answer use domain-appropriate language, or does it explain concepts as if speaking to a non-specialist?

This is about register, not complexity. A senior PM should say "requirements traceability matrix" not "the document where we track what we need to build." A senior BA should say "discovery phase" not "the beginning part where we figure things out."

---

### 6. Pattern & Framework Thinking
**Question-aware — only applied when the question is about process or approach.**

Does the answer reflect a method or framework, or does it just retell one specific case?

Senior candidates generalise from experience. They say "my approach to X is..." and then illustrate with an example. Junior candidates describe one incident without connecting it to a broader pattern.

> ❌ "So in that project at BT, we had a meeting and we decided to..."
> ✅ "When I'm managing cross-functional dependencies, I use a three-step approach: first I map all stakeholders by influence and interest, then I... For example, at BT..."

**If the question is about a specific event** (e.g. "Tell me about a time when...") — this parameter is not applied. The question itself doesn't invite framework thinking.

---

## How feedback reaches the user

Executive Language feedback appears in the **Details block** — the same block that contains the full structured feedback for each answer.

The feedback format is specific and actionable — not generic advice, but verbatim quotes from the user's actual answer with rewrites:

```
🗣 EXECUTIVE LANGUAGE

You said: "I think maybe we could have done better with the timeline"
Try instead: "The timeline slipped by two weeks. In retrospect, I would have flagged the dependency risk earlier."

You said: "I'm not sure if this is relevant but..."
Try instead: Remove the qualifier entirely. State the point.

Score: 6.5/10
```

**Tone adapts to session mode:**
- **COACH mode** — observations delivered warmly, with encouragement
- **MIRROR mode** — direct and uncompromising, no softening

---

## Session-level tracking

At the end of every session, the Executive Language average is calculated across all answers and shown in:
- The session completion summary (Telegram)
- The sessions table on the web dashboard (Exec Lang column)
- The progress bars per category

This allows the user to track Executive Language improvement across sessions — separate from domain scores.

---

## Design decisions

**Why question-aware parameters?**

Parameters 4 (Result Presence) and 6 (Pattern & Framework Thinking) are only applied when contextually relevant. This was a deliberate architectural decision.

Applying Result Presence to a question like "How do you approach stakeholder management?" would penalise the user for not mentioning a metric — when the question didn't ask for one. That's an unfair penalty that would erode trust in the scoring.

Question-aware scoring makes the system smarter and fairer.

**Why separate from content score?**

A user might score 9/10 on content (they knew the answer) but 5/10 on Executive Language (they hedged throughout and buried the conclusion). Combining these into one score would hide exactly the information the user needs to improve.

Keeping them separate gives the user a precise picture of where to invest practice time.

**Why verbatim quotes in feedback?**

Abstract feedback ("use less hedging") is easy to ignore. Seeing your own words reflected back with a rewrite makes the pattern impossible to miss — and gives you a concrete alternative to practise.

---

*Part of Cara Coach product documentation. See also: [Feature Inventory](./feature-inventory.md) · [Product Brief](./product-brief.md)*

---

## Where the model comes from

The 6 parameters weren't invented from scratch. They came from three sources: competitive analysis of executive speech coaching apps (several focus specifically on these dimensions), conversations with senior PMs and BAs about what actually gets evaluated at leadership level, and open research on professional communication patterns. There's reasonable consensus across all three on what matters most.

---

## Cultural context

Cara is calibrated for the British and American professional markets, where direct, top-down communication is consistently rewarded at senior level — regardless of the candidate's cultural background.

If you're preparing for interviews in markets where hedging is a politeness norm rather than a confidence signal (parts of Asia, for example), treat the exec language score as directional rather than prescriptive.

---

## Score calibration

Honest answer: in the current MVP, scoring relies on Claude's judgment guided by qualitative instructions — not explicit numeric rules. There's no formula that says "3 hedges = minus 1.5 points."

This is a known limitation. In practice, the scores are directionally correct and useful for tracking improvement over time — even if a 6.5 vs a 7.0 shouldn't be taken too literally. Explicit calibration logic is on the post-MVP roadmap, once there's enough real session data to work from.
