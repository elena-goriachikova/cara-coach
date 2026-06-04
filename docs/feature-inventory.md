![banner](../cara-coach-banner.svg)

# Cara Coach — Feature Inventory
Created: June 2026

---

## 🤖 TELEGRAM BOT (messages, buttons, flows)

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| `/start` command | ✅ Implemented | `bot.py` | `start()` — loads active projects, if 1 → auto-starts interview, if multiple → shows inline keyboard for selection | User types `/start`, sees project picker or goes straight to interview |
| Multi-vacancy selection | ✅ Implemented | `bot.py` | Inline keyboard with `choose\|{slug}` callback_data; `button_handler` routes to `begin_interview()` | Button per vacancy: "🏢 Company — Role" |
| Interview initiation flow | ✅ Implemented | `bot.py` | `begin_interview()` — sends 3-step progress messages, checks cache, calls `analyze_gaps → generate_questions → extract_cv_catalog` | Sees: "Analysing CV…" → "Step 1/3: gaps" → "Step 2/3: questions" → "Step 3/3: CV catalog" → "Ready!" |
| Cached start (⚡) | ✅ Implemented | `bot.py` | `load_project_cache()` skips all AI calls, sends "⚡ Using cached analysis" | Near-instant start on repeat sessions |
| Domain category announcement | ✅ Implemented | `bot.py` | First question of each domain triggers "🗂 Category: SOFT SKILLS" message | User knows which skill area they're entering |
| Question delivery with counter | ✅ Implemented | `bot.py` | `send_next_question()` formats "❓ Question N/total:\n\n{question}" | Numbered progress visible |
| Text answer handling | ✅ Implemented | `bot.py` | `handle_answer()` → `process_answer()` — evaluates typed text | Write answer, get scored feedback |
| SKIP command | ✅ Implemented | `bot.py` | Typing "SKIP" (case-insensitive) records score=0, appends `[SKIPPED]` to transcript, moves to next question | User can skip any question |
| Voice answer (Whisper) | ✅ Implemented | `bot.py`, `cara_agent.py` | `voice_handler()` downloads `.ogg`, transcribes via `openai_client.audio.transcriptions` (Whisper-1), shows transcript, calls `process_answer()` | Send voice message → see "📝 transcript" → get scored |
| Streaming score delivery | ✅ Implemented | `bot.py`, `cara_agent.py` | `ask_claude_async_stream()` yields chunks; bot edits message every 1.5s with preview; "typing…" action sent every 4s | User sees live progress "⏳ Evaluating…\n\nScore: 7…" building up |
| Score card message | ✅ Implemented | `bot.py` | After streaming: `edit_message_text` with `score_header + exec_lang_line + summary + divider` + inline keyboard | "🌟 Score: 7/10\n🗣 Exec language: 6.5/10\n\nSummary…" |
| Score delta on retry | ✅ Implemented | `bot.py`, `cara_agent.py` | `retry_previous_score` stored before domain_scores pop; `_parse_score_raw()` shows "+2", "-1", or "no change" | "📈 Score: 8/10 (+2)" after retry |
| 💡 Details button | ✅ Implemented | `bot.py` | Sends `pending_feedback[q_key]["details"]` — full structured feedback block | Positive signal, red flag, improvement tips, speech analysis, STAR tip, executive language |
| ✨ Ideal answer button | ✅ Implemented | `bot.py` | Sends `pending_feedback[q_key]["ideal"]` — senior candidate model answer based on real CV | AI-written ideal answer using candidate's own experience |
| 🔄 Try again button | ✅ Implemented | `bot.py` | Pops last score from `domain_scores`, decrements `q_counter`, resets `used_buttons`, increments `retry_count`, resends the question | "🔄 Sure, answer again:\n\n{question}" |
| ➡️ Next question button | ✅ Implemented | `bot.py` | Increments `question_index`, calls `send_next_question()` | Moves to next question |
| Dynamic button hiding | ✅ Implemented | `bot.py` | `build_keyboard()` checks `used` set; after clicking Details or Ideal, their button disappears from that message AND the re-shown keyboard | Used button never appears again on same question round |
| Button reset on retry | ✅ Implemented | `bot.py` | Retry resets `used_buttons = []` | Both Details and Ideal reappear after retry |
| Follow-up questions in context | ✅ Implemented | `bot.py` | `handle_followup_question()` — when in `waiting_for_button` state, any text is treated as a coaching question; Claude answers in context of the last Q&A+feedback | "💬 response" then buttons re-shown |
| Session completion message | ✅ Implemented | `bot.py` | `finish_session()` sends overall score, per-domain scores table, strongest/weakest question | "🏁 SESSION COMPLETE\n⭐ Overall: 7.2/10…" |
| Final debrief | ✅ Implemented | `bot.py`, `cara_agent.py` | `final_feedback()` — separate Claude call with domain averages; 120-word structured debrief: What's Working / Top 3 to Improve / Focus For Next Session | "💬 Final feedback: WHAT'S WORKING:…" |

---

## 🎙 VOICE INPUT & SPEECH ANALYSIS

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| Voice transcription | ✅ Implemented | `bot.py` | OpenAI Whisper-1 via `AsyncOpenAI`; downloads `.ogg` to temp file, transcribes with session language, deletes temp file | Send voice note → see text transcription before scoring |
| Language-aware transcription | ✅ Implemented | `bot.py` | `lang` from session settings passed to `transcriptions.create(language=lang)` | Whisper tuned to EN or RU |
| Speech pace analysis | ✅ Implemented | `cara_agent.py` | `analyze_speech()` — word count ÷ 120wpm = estimated duration; flags too slow (<90wpm), too fast (>160wpm) | "✅ Speech pace: ~45s — good pace" or ⚠️ warnings |
| Answer length analysis | ✅ Implemented | `cara_agent.py` | Duration <30s = too short, >120s = too long, else optimal | Shown in Details panel |
| Filler word detection | ✅ Implemented | `cara_agent.py` | Checks against 18-word list (EN+RU): "like", "you know", "ну", "типа" etc.; reports any word appearing ≥2× | "⚠️ Filler words: 'basically' (3x)" |
| Note: speech analysis is text-based | ⚠️ Note | `cara_agent.py` | Works on text regardless of source — applies equally to typed and transcribed voice answers | Duration/pace estimated from word count, not actual audio length |

---

## 📄 CV & JD PROCESSING

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| CV upload (TXT) | ✅ Implemented | `app.py` | Saved directly as `my_cv.txt` (global, shared across all projects) | Upload .txt in web form |
| CV upload (DOCX) | ✅ Implemented | `app.py` | `python-docx` extracts paragraph text, saves as `my_cv.txt` | Upload .docx, auto-converted |
| CV upload (PDF) | ❌ Broken | `app.py` | `cv_file.save(CV_FILE)` — saves raw bytes as .txt. No PDF parsing. Will fail or produce garbled text | PDF not supported in practice |
| JD storage per project | ✅ Implemented | `app.py` | Each project has its own `projects/{slug}/jd.txt` | Separate JD per vacancy |
| Multi-encoding CV read | ✅ Implemented | `cara_agent.py` | `ingest_cv_jd()` tries UTF-8 → UTF-16 → latin-1 → cp1252 | Handles most file encodings |
| CV gap analysis | ✅ Implemented | `cara_agent.py` | `analyze_gaps()` — Claude compares CV text vs JD, identifies gaps and recommendations | Not user-visible directly; used to generate questions |
| CV story catalog extraction | ✅ Implemented | `cara_agent.py` | `extract_cv_catalog()` — one-time Claude call extracting: ROLES / TOP STORIES / KEY METRICS / DOMAINS / STRONGEST MATCH in structured plain text | Enables personalised ideal answers using real CV data |
| Cache invalidation on CV/JD change | ✅ Implemented | `app.py` | On `/submit`: compares new vs stored JD bytes; if JD or CV changed → deletes `cached_analysis.json` | Stale cache cleared automatically |

---

## ❓ QUESTION GENERATION

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| 3-domain question generation | ✅ Implemented | `cara_agent.py` | `generate_questions()` — Claude prompt with strict format; parses into `{domain: [questions]}` dict | 6 questions total: 2 soft skills, 2 hard skills, 2 behavioural |
| Domain parsing | ✅ Implemented | `cara_agent.py` | Line-by-line parser: detects domain header, extracts numbered questions | Robust to Claude's markdown variations |
| Questions tailored to CV gaps | ✅ Implemented | `cara_agent.py` | Questions generated from `gaps` output (CV vs JD analysis) | Questions specific to candidate's actual profile |
| Fixed question count | ⚠️ Hardcoded | `cara_agent.py` | `NUM_QUESTIONS = 6`, `questions_per_domain = max(1, 6//3) = 2` | Always 2 questions per domain, 6 total — no UI control |

---

## 🎯 SCORING & FEEDBACK

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| Per-answer scoring (1–10) | ✅ Implemented | `cara_agent.py`, `bot.py` | `_build_score_prompt()` → Claude returns structured response; `_parse_score_raw()` extracts fields | Score 1–10 per answer |
| Coach mode | ✅ Implemented | `cara_agent.py` | Prompt style: "honest but supportive. Highlight strengths, then point out what to improve. Warm but honest" | Balanced, encouraging feedback |
| Mirror mode | ✅ Implemented | `cara_agent.py` | Prompt style: "direct and uncompromising. No softening. Name weaknesses plainly" | Brutal honesty, no sugarcoating |
| Positive signal | ✅ Implemented | `cara_agent.py`, `bot.py` | `POSITIVE_TITLE` + `POSITIVE_BODY` from Claude | "✅ POSITIVE SIGNAL\n{title}\n\n{body}" in Details |
| Red flag | ✅ Implemented | `cara_agent.py`, `bot.py` | `FLAG_TITLE` + `FLAG_BODY` from Claude | "🚩 RED FLAG\n{title}\n\n{body}" in Details |
| Improvement tips | ✅ Implemented | `cara_agent.py`, `bot.py` | `IMPROVE` — 3–4 numbered tips; bot converts `(1)` → `1️⃣` | "💡 HOW TO STRENGTHEN\n1️⃣…2️⃣…" in Details |
| STAR tip | ✅ Implemented | `cara_agent.py`, `bot.py` | `STAR_TIP` — how to apply STAR method to this specific answer | "🎯 INTERVIEW TIP\n{tip}" in Details |
| Ideal answer (CV-grounded) | ✅ Implemented | `cara_agent.py`, `bot.py` | `IDEAL` — Claude writes model answer using ONLY real CV stories. Explicit instruction: do NOT invent experience at target company | "✨ STRONG ANSWER EXAMPLE\n\n{ideal}" |
| Typo/grammar tolerance | ✅ Implemented | `cara_agent.py` | Prompt: "this is a transcription of live speech — ignore typos, grammar, spelling. Evaluate only meaning and content" | Voice transcription artefacts don't penalise score |
| Per-domain score accumulation | ✅ Implemented | `bot.py` | `domain_scores = {domain: [scores]}` updated after each answer | Per-domain averages at session end |
| Overall score | ✅ Implemented | `bot.py` | Mean of all `question_scores` | Final "⭐ Overall: 7.2/10" |
| Strongest/weakest question | ✅ Implemented | `bot.py` | `max/min(all_scores, key=lambda x: x["score"])` | Highlighted in session complete message |

---

## 🗣 EXECUTIVE LANGUAGE SCORING

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| Exec language score (float 1–10) | ✅ Implemented | `cara_agent.py`, `bot.py` | Separate `EXEC_LANG_SCORE` field in Claude response; float (e.g. 6.5) | Shown in score card: "🗣 Exec language: 6.5/10" |
| 6-parameter assessment | ✅ Implemented | `cara_agent.py` | Evaluates: (1) Top-down structure, (2) Hedging density, (3) Apology language density, (4) Result presence (question-aware), (5) Professional vocabulary, (6) Pattern & framework thinking (question-aware) | Composite score reflecting executive communication style |
| Question-aware parameter skipping | ✅ Implemented | `cara_agent.py` | Parameters 4 and 6 only apply when contextually relevant; prompt explicitly instructs Claude to skip inapplicable ones | No unfair penalties for opinion/process questions |
| Exec language feedback with verbatim quotes | ✅ Implemented | `cara_agent.py`, `bot.py` | `EXEC_LANG_FEEDBACK` — 1–2 exact quotes from answer with rewrites in senior executive register; format: "You said: [quote]\nTry instead: [rewrite]" | Concrete examples visible in Details panel |
| Exec language average per session | ✅ Implemented | `bot.py` | `exec_lang_scores[]` accumulated; averaged in `update_session_snapshot()` and `finish_session()` | Shown in session summary and website dashboard |

---

## 💾 SESSION MANAGEMENT & STORAGE

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| In-memory session state | ✅ Implemented | `bot.py` | `sessions = {chat_id: dict}` — live state including question progress, scores, transcript, feedback, buttons | Bot maintains full session context |
| Session persistence to disk | ✅ Implemented | `bot.py` | `bot_sessions.json` — saved after every meaningful action via `save_sessions()` | Sessions survive bot restart |
| Session history logging | ✅ Implemented | `bot.py` | `session_history.json` per project — updated after every answer (`update_session_snapshot()`) and on completion | Real-time progress visible on website even mid-session |
| Session snapshot fields | ✅ Implemented | `bot.py` | Saves: `session_id`, `date`, `overall`, `domain_averages`, `exec_lang_avg`, `questions_answered`, `questions_total`, `skipped`, `retry_count`, `completed`, `export_file` | Full metadata per session |
| Multi-project support | ✅ Implemented | `bot.py`, `app.py` | Each project has its own `projects/{slug}/` directory with `settings.json`, `jd.txt`, `cached_analysis.json`, `session_history.json` | Multiple vacancies, isolated data |
| Single bot instance enforcement | ✅ Implemented | `bot.py` | `ensure_single_instance()` — `pgrep -f bot.py`, kills all other instances on startup | Prevents duplicate bot responses |
| Retry count tracking | ✅ Implemented | `bot.py` | `session["retry_count"]` incremented on every retry, stored in session snapshot | Visible in website sessions table |
| Vacancy status (active/closed) | ✅ Implemented | `app.py`, `bot.py` | `status` field in `settings.json`; bot skips `closed`/`cancelled` vacancies in `/start` | Closed vacancies don't appear in bot |
| Reopen vacancy | ✅ Implemented | `app.py`, `frontend` | `POST /api/projects/{slug}/status` with `{"status":"active"}`; history untouched | Website button toggles Close ↔ Reopen Vacancy |

---

## 🌐 WEB DASHBOARD (Flask)

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| Project creation form | ✅ Implemented | `app.py`, `frontend` | `POST /submit` — saves `settings.json`, `jd.txt`; creates `projects/{slug}/` directory | Fill role, company, JD, language, mode, date → save |
| Auto-slug generation | ✅ Implemented | `app.py` | `make_slug(company, role)` — lowercase, underscores, alphanumeric only, max 60 chars | Stable filesystem-safe project ID |
| Project editing | ✅ Implemented | `app.py`, `frontend` | `editProject()` re-populates form with existing data, submits with existing `slug` to update in place | Edit any project field |
| CV upload via web | ✅ Implemented | `app.py` | `.txt` saved directly; `.docx` parsed via `python-docx`; single global `my_cv.txt` shared across all projects | Upload once, used everywhere |
| Project sidebar | ✅ Implemented | `frontend` | Sorted by last session date; shows company name, role, status badge | Quick navigation between vacancies |
| Project status badge | ✅ Implemented | `frontend` | Badges: "New" (no sessions), blank (active with sessions), "Closed" | Visual project state |
| Vacancy detail card | ✅ Implemented | `frontend` | Shows: role, company, language, mode badge, date, questions count, estimated time, session window, CV cache status | Full project overview |
| Open in Telegram button | ✅ Implemented | `frontend` | Deep link `https://t.me/CaraCoachBot` — opens bot chat | One-click to start practicing |
| Sessions panel (toggle) | ✅ Implemented | `frontend` | `toggleSessions()` — shows/hides panel below project card; loads sessions via `GET /api/sessions/{slug}` | Click "📊 Sessions" button |
| Session statistics (metric cards) | ✅ Implemented | `frontend` | Sessions count, last score (with delta vs previous), best score, average, exec language average | Visual summary above table |
| Progress bars per category | ✅ Implemented | `frontend` | `renderSessions()` computes averages across all completed sessions; animated bars for Soft / Hard / Behavioural / Exec lang | Visual skill breakdown |
| Sessions table | ✅ Implemented | `frontend` | Columns: Date, Overall, Soft, Hard, Behavioural, Exec Lang, Retried, Export | Full history at a glance |
| Close/Reopen vacancy | ✅ Implemented | `app.py`, `frontend` | `closeProject()` — toggle function; button text changes dynamically | "Close Vacancy" ↔ "↩ Reopen Vacancy" |

---

## 📦 EXPORT & REPORTING

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| Per-session MD export | ✅ Implemented | `bot.py` | `generate_session_export()` — full Markdown with all Q&A, feedback, ideal answers, scores table, final feedback; saved to `projects/{slug}/export_{timestamp}.md` at session end | Auto-generated at end of every session |
| Download individual session export | ✅ Implemented | `app.py`, `frontend` | `GET /api/projects/{slug}/export/{filename}` — Flask `send_file`; download button in sessions table | Click 💾 in Export column |
| Date range export | ✅ Implemented | `app.py`, `frontend` | `GET /api/projects/{slug}/export/range?from=&to=` — filters completed sessions, concatenates individual MD export files, serves via `BytesIO` | Date pickers + "📅 Export" button in sessions panel |
| Export MD structure | ✅ Implemented | `bot.py` | Per question: ❓ Question / 🗣 My Answer / 💡 Feedback / ✨ Ideal Answer; then Session Summary table; then Final Feedback | Clean, readable Markdown |
| Export fallback for legacy sessions | ✅ Implemented | `app.py` | Range export handles sessions without `export_file`: shows summary table with available scores instead | Old sessions don't break range exports |

---

## ⚡ CACHE & PERFORMANCE

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| Analysis cache | ✅ Implemented | `bot.py` | `cached_analysis.json` per project stores `gaps`, `questions_by_domain`, `cv_catalog` | Subsequent sessions start in seconds |
| Smart cache invalidation | ✅ Implemented | `app.py` | Cache deleted only when JD or CV actually changes (byte-level comparison) | Cache survives edits to date/mode/language |
| Streaming response | ✅ Implemented | `bot.py`, `cara_agent.py` | `ask_claude_async_stream()` — Anthropic streaming API; bot edits message live | No long silent wait; user sees progress |
| Timing logs | ✅ Implemented | `bot.py` | `print(f"⏱ streaming score: {time.time()-_t:.1f}s")` and voice: download / transcribe / total | Console performance monitoring |

---

## 👥 MULTI-USER & ARCHITECTURE

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| Multi-chat support | ✅ Implemented | `bot.py` | `sessions = {chat_id: dict}` — each Telegram user has isolated session state | Multiple users can use the bot simultaneously |
| Single user assumption (CV) | ⚠️ Partial | `app.py` | `my_cv.txt` is global — one CV for all projects, one user | Not designed for multiple users with different CVs |
| API keys from macOS Keychain | ✅ Implemented | `bot.py`, `cara_agent.py` | `security find-generic-password` — reads TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY from system Keychain | No `.env` file needed; secrets never in code |
| Dual AI providers | ✅ Implemented | `bot.py`, `cara_agent.py` | Anthropic Claude (`claude-haiku-4-5-20251001`) for all scoring/feedback; OpenAI Whisper-1 for voice transcription only | Best-of-breed for each task |

---

## 🌍 LANGUAGE SUPPORT

| Feature | Status | Files | Technical | User experience |
|---|---|---|---|---|
| English mode | ✅ Implemented | `cara_agent.py` | `lang_instruction = "Respond in English."` passed to all Claude prompts | All output in English |
| Russian mode | ✅ Implemented | `cara_agent.py` | `lang_instruction = "Отвечай на русском языке."` passed to all Claude prompts | All output in Russian |
| Language-aware Whisper | ✅ Implemented | `bot.py` | `language=lang` in transcription call | Whisper optimised for the selected language |
| Language selector in UI | ✅ Implemented | `frontend` | Dropdown: English / Russian (and others) | Set per project |
| Filler words in both languages | ✅ Implemented | `cara_agent.py` | Separate lists for Russian ("ну", "типа", "значит"…) and English ("like", "basically"…) | Detects fillers regardless of session language |

---

## 🚫 NOT YET IMPLEMENTED / STUBS

| Feature | Status | Notes |
|---|---|---|
| PDF CV parsing | ❌ Broken | `app.py` saves PDF bytes directly as `.txt` — produces garbled text. Needs `PyPDF2` or `pdfminer` |
| Auth / login system | ❌ Stub | `doSignup()` and `doLogin()` functions exist in JS but do nothing — no server-side auth |
| Configurable question count | ❌ Hardcoded | `NUM_QUESTIONS = 6` in `cara_agent.py` — no UI control |
| Question count UI | ❌ Placeholder | "9 · 3 categories" hardcoded in HTML — not computed from actual questions |
| Estimated time UI | ❌ Hardcoded | "~30 minutes" hardcoded in HTML — not computed |
| Session window display | ❌ Hardcoded | "24 hours" hardcoded in HTML — no actual enforcement |
| Multi-user CV | ❌ Not implemented | `my_cv.txt` is a single global file — no per-user CV storage |
| Progress auto-refresh on website | ❌ Not implemented | Sessions panel requires manual open/reload — no live polling |
| `liora.env` file | ❓ Legacy | File exists in project root but not imported anywhere in current code |
| `prompt.txt`, `session_settings.json` | ❓ Legacy | Exist in project root but not referenced in current code |

---

*Part of Cara Coach product documentation. See also:  [Product Brief](./product-brief.md)  · [Executive Language Scoring](./executive-language-scoring.md) · [Prompt Architecture](./prompt-architecture.md)  *

---


![footer](../cara-coach-int-footer.svg)
