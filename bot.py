import re
import json
import os
import signal
import subprocess
import tempfile
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import AsyncOpenAI

from cara_agent import (
    ingest_cv_jd, analyze_gaps, generate_questions,
    extract_cv_catalog, final_feedback,
    ask_claude_async, ask_claude_async_stream, _build_score_prompt, _parse_score_raw
)

# ── API tokens from macOS Keychain ────────────────────────────────────────────
def _keychain(service):
    return subprocess.run(
        ["security", "find-generic-password", "-a", subprocess.getoutput("whoami"), "-s", service, "-w"],
        capture_output=True, text=True
    ).stdout.strip()

token        = _keychain("TELEGRAM_BOT_TOKEN")
openai_key   = _keychain("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=openai_key)

PROJECTS_DIR  = "projects"
PID_FILE      = "bot.pid"


# ── Project management (multi-vacancy support) ────────────────────────────────
def list_projects():
    projects = []
    if not os.path.exists(PROJECTS_DIR):
        return projects
    for slug in os.listdir(PROJECTS_DIR):
        path = os.path.join(PROJECTS_DIR, slug, "settings.json")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            s = json.load(f)
        # Skip closed / cancelled vacancies
        if s.get("status") in ("closed", "cancelled"):
            continue
        s["slug"] = slug
        # Last session date for sorting
        history_path = os.path.join(PROJECTS_DIR, slug, "session_history.json")
        last_session = ""
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
            last_session = max((h.get("session_id", "") for h in history), default="")
        s["last_session"] = last_session
        projects.append(s)
    # Most recently practiced first; never-practiced go to the end
    projects.sort(key=lambda p: p.get("last_session") or "0000", reverse=True)
    return projects

def load_project(slug):
    path = os.path.join(PROJECTS_DIR, slug, "settings.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def load_project_cache(slug):
    path = os.path.join(PROJECTS_DIR, slug, "cached_analysis.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_project_cache(slug, gaps, questions_by_domain, cv_catalog):
    path = os.path.join(PROJECTS_DIR, slug, "cached_analysis.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "gaps": gaps,
            "questions_by_domain": questions_by_domain,
            "cv_catalog": cv_catalog
        }, f, ensure_ascii=False, indent=2)

def update_session_snapshot(session, completed=False):
    """Saves / updates the current session snapshot in session_history.json.
    Called after every answer and on completion — works for any number of questions."""
    slug = session.get("slug")
    if not slug:
        return
    path = os.path.join(PROJECTS_DIR, slug, "session_history.json")

    all_q    = session.get("question_scores", [])
    scored_q = [q for q in all_q if q["score"] > 0]
    skipped  = sum(1 for q in all_q if q["score"] == 0)
    overall  = round(sum(q["score"] for q in scored_q) / len(scored_q), 1) if scored_q else 0

    domain_averages = {
        d: round(sum(s) / len(s), 1) if s else 0
        for d, s in session.get("domain_scores", {}).items()
    }
    total_q = sum(len(q) for q in session.get("questions_by_domain", {}).values())

    el_raw = session.get("exec_lang_scores", [])
    try:
        exec_lang_avg = round(sum(float(s) for s in el_raw) / len(el_raw), 1) if el_raw else None
    except (ValueError, TypeError):
        exec_lang_avg = None

    entry = {
        "session_id":        session.get("session_start", ""),
        "date":              session.get("session_start", "")[:10],
        "overall":           overall,
        "domain_averages":   domain_averages,
        "exec_lang_avg":     exec_lang_avg,
        "questions_answered": len(scored_q),
        "questions_total":   total_q,
        "skipped":           skipped,
        "retry_count":       session.get("retry_count", 0),
        "completed":         completed,
    }

    history = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)

    # Update existing session entry, or append if new
    sid = entry["session_id"]
    idx = next((i for i, h in enumerate(history) if h.get("session_id") == sid), None)
    if idx is not None:
        history[idx] = entry
    else:
        history.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def ensure_single_instance():
    """Kills all previous bot.py instances to prevent duplicate polling."""
    current_pid = os.getpid()
    result = subprocess.run(["pgrep", "-f", "bot.py"], capture_output=True, text=True)
    pids = [int(p) for p in result.stdout.strip().split("\n") if p and int(p) != current_pid]
    if pids:
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        print(f"⚠️ Stopped {len(pids)} previous bot instance(s): {pids}")
        time.sleep(2)

    with open(PID_FILE, "w") as f:
        f.write(str(current_pid))

def cleanup_pid():
    """Removes the PID file on exit."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

ensure_single_instance()


# ── Session state (chat_id → dict) ───────────────────────────────────────────
SESSIONS_FILE = "bot_sessions.json"

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_sessions(sessions):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sessions.items()}, f, ensure_ascii=False, indent=2)

sessions = load_sessions()


# ── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id  = update.effective_chat.id
    projects = list_projects()

    if not projects:
        await update.message.reply_text(
            "⚠️ No vacancies found.\n\nGo to http://localhost:5001 and add a vacancy first."
        )
        return

    if len(projects) == 1:
        # Single vacancy — start immediately
        await begin_interview(context, chat_id, projects[0]["slug"])
    else:
        # Multiple vacancies — show selection menu
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"🏢 {p.get('company', '?')} — {p.get('role', '?')}",
                callback_data=f"choose|{p['slug']}"
            )]
            for p in projects
        ])
        await update.message.reply_text(
            "👋 Hi! I'm Cara Coach.\n\nChoose a vacancy to practice:",
            reply_markup=keyboard
        )


# ── Start interview for the selected vacancy ──────────────────────────────────
async def begin_interview(context: ContextTypes.DEFAULT_TYPE, chat_id: int, slug: str):
    settings = load_project(slug)
    if not settings:
        await context.bot.send_message(chat_id=chat_id, text="❌ Vacancy not found. Check the website.")
        return

    lang    = settings.get("lang", "en")
    role    = settings.get("role", "—")
    company = settings.get("company", "—")

    await context.bot.send_message(chat_id=chat_id, text=
        f"👋 Hi! I'm Cara Coach.\n\n📋 Preparing interview:\n"
        f"• Role: {role}\n• Company: {company}\n\n"
        f"Analysing CV and job description… ⏳"
    )

    try:
        jd_path = os.path.join(PROJECTS_DIR, slug, "jd.txt")
        cv, jd  = ingest_cv_jd("my_cv.txt", jd_path)

        cache = load_project_cache(slug)
        if cache:
            gaps                = cache["gaps"]
            questions_by_domain = cache["questions_by_domain"]
            cv_catalog          = cache.get("cv_catalog", "")
            await context.bot.send_message(chat_id=chat_id, text="⚡ Using cached analysis. Questions ready!")
        else:
            await context.bot.send_message(chat_id=chat_id, text="🔍 Step 1/3: Analysing gaps…")
            gaps                = await analyze_gaps(cv, jd, lang=lang)
            await context.bot.send_message(chat_id=chat_id, text="❓ Step 2/3: Generating questions…")
            questions_by_domain = await generate_questions(gaps, lang=lang)
            await context.bot.send_message(chat_id=chat_id, text="📋 Step 3/3: Extracting your story catalog…")
            cv_catalog          = await extract_cv_catalog(cv, jd, lang=lang)
            save_project_cache(slug, gaps, questions_by_domain, cv_catalog)

        from datetime import datetime
        sessions[chat_id] = {
            "settings":            settings,
            "slug":                slug,
            "session_start":       datetime.now().isoformat(),
            "cv_text":             cv_catalog or cv,
            "questions_by_domain": questions_by_domain,
            "domain_list":         list(questions_by_domain.keys()),
            "domain_index":        0,
            "question_index":      0,
            "domain_scores":       {d: [] for d in questions_by_domain},
            "question_scores":     [],
            "exec_lang_scores":    [],
            "retry_count":         0,
            "transcript_lines":    [],
            "waiting_for_answer":  False,
            "waiting_for_button":  False,
            "current_question":    None,
            "current_domain":      None,
            "q_counter":           0,
            "pending_feedback":    {},
        }
        save_sessions(sessions)

        total   = sum(len(q) for q in questions_by_domain.values())
        domains = ", ".join(questions_by_domain.keys())
        await context.bot.send_message(chat_id=chat_id, text=
            f"✅ Analysis complete! Starting interview.\n\n"
            f"Total questions: {total}\nCategories: {domains}\n\n"
            f"Answer as you would in a real interview. Good luck! 🚀"
        )
        await send_next_question(context, chat_id)

    except FileNotFoundError as e:
        await context.bot.send_message(chat_id=chat_id,
            text=f"❌ File not found: {e}\n\nMake sure your CV is uploaded via the website.")
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")


# ── Send next question ────────────────────────────────────────────────────────
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    session = sessions.get(chat_id)
    if not session:
        return

    domain_list = session["domain_list"]
    d_idx = session["domain_index"]
    q_idx = session["question_index"]

    # All questions answered — finish session
    if d_idx >= len(domain_list):
        await finish_session(context, chat_id)
        return

    current_domain = domain_list[d_idx]
    questions = session["questions_by_domain"][current_domain]

    # Move to next domain
    if q_idx >= len(questions):
        session["domain_index"] += 1
        session["question_index"] = 0
        await send_next_question(context, chat_id)
        return

    # Announce new domain at its first question
    if q_idx == 0:
        await context.bot.send_message(chat_id=chat_id, text=f"🗂 Category: {current_domain.upper()}")

    question = questions[q_idx]
    session["current_question"]  = question
    session["current_domain"]    = current_domain
    session["waiting_for_answer"] = True
    session["waiting_for_button"] = False
    save_sessions(sessions)

    answered = sum(len(s) for s in session["domain_scores"].values())
    total    = sum(len(q) for q in session["questions_by_domain"].values())

    await context.bot.send_message(chat_id=chat_id, text=f"❓ Question {answered+1}/{total}:\n\n{question}")


# ── Dynamic keyboard (hide already-used Details/Ideal buttons) ────────────────
def build_keyboard(q_key: str, chat_id: int, used: set) -> InlineKeyboardMarkup:
    row1 = []
    if "details" not in used:
        row1.append(InlineKeyboardButton("💡 Details",     callback_data=f"details_{q_key}_{chat_id}"))
    if "ideal" not in used:
        row1.append(InlineKeyboardButton("✨ Ideal answer", callback_data=f"ideal_{q_key}_{chat_id}"))
    row2 = [
        InlineKeyboardButton("🔄 Try again",    callback_data=f"retry_{q_key}_{chat_id}"),
        InlineKeyboardButton("➡️ Next question", callback_data=f"next_{q_key}_{chat_id}"),
    ]
    rows = ([row1] if row1 else []) + [row2]
    return InlineKeyboardMarkup(rows)


# ── Follow-up question handler ────────────────────────────────────────────────
async def handle_followup_question(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_question: str):
    """Answers a follow-up question in the context of the last Q&A round, then re-shows the buttons."""
    session = sessions.get(chat_id)
    if not session:
        return

    q_key   = str(max(0, session.get("q_counter", 1) - 1))
    fb      = session.get("pending_feedback", {}).get(q_key, {})
    lang    = session["settings"].get("lang", "en")
    lang_instruction = "Respond in English." if lang == "en" else "Отвечай на русском языке."

    interview_question = fb.get("question", session.get("current_question", ""))

    # Get the candidate's last answer from the transcript
    transcript = session.get("transcript_lines", [])
    candidate_answer = ""
    if transcript:
        last = transcript[-1]
        if "A: " in last:
            candidate_answer = last.split("A: ", 1)[-1].strip()

    parts = [f"Interview question: {interview_question}"]
    if candidate_answer:
        parts.append(f"Candidate's answer: {candidate_answer}")
    if fb.get("details"):
        parts.append(f"Feedback given:\n{fb['details']}")
    if fb.get("ideal"):
        parts.append(f"Ideal answer shown:\n{fb['ideal']}")

    prompt = (
        f"You are Cara Coach, an AI interview coach. "
        f"The candidate just received feedback and has a follow-up question.\n\n"
        f"{chr(10).join(parts)}\n\n"
        f"Candidate's question: {user_question}\n\n"
        f"Answer in 2-3 sentences, stay in your coaching role. {lang_instruction}"
    )

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    response = await ask_claude_async(prompt)
    await context.bot.send_message(chat_id=chat_id, text=f"💬 {response}")

    # Re-show buttons, hiding already-used ones
    used = set(fb.get("used_buttons", []))
    keyboard = build_keyboard(q_key, chat_id, used)
    await context.bot.send_message(chat_id=chat_id, text="👆 Continue:", reply_markup=keyboard)


# ── Incoming text message handler ─────────────────────────────────────────────
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return  # ignore voice, edited messages, and other non-text updates

    chat_id = update.effective_chat.id
    session = sessions.get(chat_id)

    if not session:
        await update.message.reply_text("Write /start to begin the interview.")
        return

    if session.get("waiting_for_button"):
        await handle_followup_question(context, chat_id, update.message.text.strip())
        return

    if not session.get("waiting_for_answer"):
        await update.message.reply_text("Write /start to begin the interview.")
        return

    answer   = update.message.text.strip()
    question = session["current_question"]
    domain   = session["current_domain"]

    # SKIP
    if answer.upper() == "SKIP":
        session["domain_scores"][domain].append(0)
        session["transcript_lines"].append(f"## {domain.upper()}\nQ: {question}\nA: [SKIPPED]")
        session["waiting_for_answer"] = False
        session["question_index"] += 1
        save_sessions(sessions)
        await update.message.reply_text("⏭ Question skipped. Moving on.")
        await send_next_question(context, chat_id)
        return

    await process_answer(context, chat_id, answer)


# ── Core answer processing logic ──────────────────────────────────────────────
async def process_answer(context: ContextTypes.DEFAULT_TYPE, chat_id: int, answer: str):
    session = sessions.get(chat_id)
    if not session:
        return

    question = session["current_question"]
    domain   = session["current_domain"]
    mode     = session["settings"].get("mode", "coach")
    lang     = session["settings"].get("lang", "en")

    session["waiting_for_answer"] = False
    session["transcript_lines"].append(f"## {domain.upper()}\nQ: {question}\nA: {answer}")
    previous_score = session.pop("retry_previous_score", None)
    save_sessions(sessions)

    _t = time.time()

    # Streaming — show live progress while Claude evaluates
    prompt = _build_score_prompt(question, answer, session["cv_text"], mode, lang)
    msg = await context.bot.send_message(chat_id=chat_id, text="⏳ Evaluating…")
    buffer = ""
    last_edit   = time.time()
    last_typing = time.time()

    async for chunk in ask_claude_async_stream(prompt):
        buffer += chunk
        now = time.time()

        # Send "typing" action every 4s so the user knows the bot is alive
        if now - last_typing > 4:
            try:
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                last_typing = now
            except Exception:
                pass

        # Update the preview message every 1.5s
        if now - last_edit > 1.5:
            preview = buffer.replace('*', '')[:400]
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg.message_id,
                    text=f"⏳ Evaluating…\n\n{preview}"
                )
                last_edit = now
            except Exception:
                pass

    (score_num_str, score_header, summary, pos_title, pos_body,
     flag_title, flag_body, improve, star_tip, speech, ideal,
     exec_lang_score, exec_lang_feedback) = _parse_score_raw(buffer, answer, previous_score)

    print(f"⏱ streaming score: {time.time()-_t:.1f}s")
    try:
        score_num = int(score_num_str)
    except (ValueError, TypeError):
        match = re.search(r'\b([1-9]|10)\b', score_num_str or "")
        score_num = int(match.group(1)) if match else None

    if score_num:
        session["domain_scores"][domain].append(score_num)
        session["question_scores"].append({"question": question, "score": score_num})

    if exec_lang_score:
        session.setdefault("exec_lang_scores", []).append(exec_lang_score)

    q_key = str(session.get("q_counter", 0))
    improve_formatted = (improve
        .replace("(1)", "1️⃣").replace("(2)", "2️⃣")
        .replace("(3)", "3️⃣").replace("(4)", "4️⃣")
    )
    div = "──────────────"

    # Executive language section for Details panel
    if exec_lang_score:
        el_section = f"🗣 EXECUTIVE LANGUAGE: {exec_lang_score}/10"
        if exec_lang_feedback and exec_lang_feedback.strip().lower() != "none":
            el_section += f"\n\n{exec_lang_feedback}"
        el_block = f"\n\n{div}\n{el_section}"
    else:
        el_block = ""

    session["pending_feedback"][q_key] = {
        "details": (
            f"✅ POSITIVE SIGNAL\n{pos_title}\n\n{pos_body}\n\n{div}\n"
            f"🚩 RED FLAG\n{flag_title}\n\n{flag_body}\n\n{div}\n"
            f"💡 HOW TO STRENGTHEN\n\n{improve_formatted}\n\n{div}\n"
            f"🎤 SPEECH ANALYSIS\n\n{speech}\n\n{div}\n"
            f"🎯 INTERVIEW TIP\n\n{star_tip}"
            f"{el_block}"
        ),
        "ideal":        f"✨ STRONG ANSWER EXAMPLE\n\n{ideal}" if ideal else "",
        "domain":       domain,
        "question":     question,
        "used_buttons": [],
    }
    session["q_counter"] = session.get("q_counter", 0) + 1
    session["waiting_for_button"] = True
    save_sessions(sessions)
    update_session_snapshot(session)   # save partial progress after every answer

    # Exec language score line shown in the immediate score card
    exec_lang_line = f"\n🗣 Exec language: {exec_lang_score}/10" if exec_lang_score else ""

    # Replace the streaming message with the final score card + buttons
    keyboard = build_keyboard(q_key, chat_id, set())
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg.message_id,
        text=f"{score_header}{exec_lang_line}\n\n{summary}\n\n{div}",
        reply_markup=keyboard
    )


# ── Voice transcription ───────────────────────────────────────────────────────
async def transcribe_voice(file_path: str, lang: str = "en") -> str:
    with open(file_path, "rb") as audio_file:
        transcript = await openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=lang
        )
    return transcript.text


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return

    chat_id = update.effective_chat.id
    session = sessions.get(chat_id)

    if not session:
        await update.message.reply_text("Write /start to begin the interview.")
        return

    if session.get("waiting_for_button"):
        await update.message.reply_text("👆 Please use the buttons above to continue.")
        return

    if not session.get("waiting_for_answer"):
        await update.message.reply_text("Write /start to begin the interview.")
        return

    lang = session["settings"].get("lang", "en")
    await update.message.reply_text("🎙 Transcribing…")

    voice = update.message.voice
    t0 = time.time()

    file = await context.bot.get_file(voice.file_id)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await file.download_to_drive(tmp_path)
        print(f"⏱ Download:    {time.time()-t0:.1f}s")

        answer_text = await transcribe_voice(tmp_path, lang)
        print(f"⏱ Transcribe:  {time.time()-t0:.1f}s")
    finally:
        os.unlink(tmp_path)

    await update.message.reply_text(f"📝 {answer_text}")
    await process_answer(context, chat_id, answer_text)
    print(f"⏱ Total:       {time.time()-t0:.1f}s")


# ── Inline button handler ─────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Vacancy selection from /start menu
    if query.data.startswith("choose|"):
        slug = query.data[7:]
        await query.message.edit_reply_markup(reply_markup=None)
        await begin_interview(context, query.message.chat_id, slug)
        return

    parts   = query.data.split("_")
    action  = parts[0]
    q_key   = parts[1]
    chat_id = int(parts[2])

    session = sessions.get(chat_id)
    if not session:
        await query.message.reply_text("Session expired. Write /start to begin again.")
        return

    fb   = session.get("pending_feedback", {}).get(q_key, {})
    used = set(fb.get("used_buttons", []))

    if action == "details":
        # Mark as used before sending so the re-shown keyboard already hides it
        if "details" not in used:
            used.add("details")
            session["pending_feedback"][q_key]["used_buttons"] = list(used)
            save_sessions(sessions)

        keyboard = build_keyboard(q_key, chat_id, used)
        try:
            await query.message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        text = fb.get("details", "")
        if text:
            try:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
            except Exception as e:
                print(f"⚠️ details send error: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text[:4000] + "\n\n[truncated]",
                    reply_markup=keyboard
                )

    elif action == "ideal":
        # Mark as used before sending so the re-shown keyboard already hides it
        if "ideal" not in used:
            used.add("ideal")
            session["pending_feedback"][q_key]["used_buttons"] = list(used)
            save_sessions(sessions)

        keyboard = build_keyboard(q_key, chat_id, used)
        try:
            await query.message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass
        text = fb.get("ideal", "")
        print(f"[ideal] q_key={q_key} | fb keys={list(fb.keys())} | ideal len={len(text)}")
        if text:
            try:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
            except Exception as e:
                print(f"⚠️ ideal send error: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text[:4000] + "\n\n[truncated]",
                    reply_markup=keyboard
                )
        else:
            print(f"[ideal] EMPTY — pending_feedback keys: {list(session.get('pending_feedback',{}).keys())}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Ideal answer wasn't generated for this question. Try again ↓",
                reply_markup=keyboard
            )

    elif action == "retry":
        domain = fb.get("domain", session.get("current_domain"))
        domain_scores = session["domain_scores"].get(domain, [])
        if domain_scores:
            session["retry_previous_score"] = domain_scores[-1]
            session["domain_scores"][domain] = domain_scores[:-1]
            if session["question_scores"]:
                session["question_scores"].pop()
        # Reset used buttons so Details and Ideal appear again for the new attempt
        session["pending_feedback"][q_key]["used_buttons"] = []
        session["retry_count"] = session.get("retry_count", 0) + 1
        session["waiting_for_answer"] = True
        session["waiting_for_button"] = False
        session["q_counter"] = max(0, session.get("q_counter", 1) - 1)
        save_sessions(sessions)
        await query.message.edit_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔄 Sure, answer again:\n\n{fb.get('question', session.get('current_question', ''))}"
        )

    elif action == "next":
        session["question_index"] += 1
        session["waiting_for_button"] = False
        save_sessions(sessions)
        await query.message.edit_reply_markup(reply_markup=None)
        await send_next_question(context, chat_id)


# ── Session Markdown export ───────────────────────────────────────────────────
def generate_session_export(session: dict, final_feedback_text: str = "") -> str:
    """Returns a full Markdown document of everything shown to the user in the session."""
    settings      = session.get("settings", {})
    role          = settings.get("role", "—")
    company       = settings.get("company", "—")
    mode          = settings.get("mode", "coach").capitalize()
    session_start = session.get("session_start", "")
    date_str      = session_start[:10]
    time_str      = session_start[11:16] if len(session_start) > 10 else ""

    lines = [
        f"# Interview Session — {role} at {company}",
        "",
        f"**Date:** {date_str} {time_str}",
        f"**Mode:** {mode}",
        "",
        "---",
        "",
    ]

    q_counter       = session.get("q_counter", 0)
    pending         = session.get("pending_feedback", {})
    question_scores = session.get("question_scores", [])
    el_scores       = session.get("exec_lang_scores", [])

    # Build answer map: question_text → answer_text (from transcript)
    answers_map = {}
    for t in session.get("transcript_lines", []):
        if "\nQ: " in t and "\nA: " in t:
            after_q = t.split("\nQ: ", 1)[1]
            q_text, a_text = after_q.split("\nA: ", 1)
            answers_map[q_text.strip()] = a_text.strip()

    for i in range(q_counter):
        q_key    = str(i)
        fb       = pending.get(q_key, {})
        question = fb.get("question", "")
        domain   = fb.get("domain", "")
        answer   = answers_map.get(question, "[answer not recorded]")

        score_parts = []
        if i < len(question_scores):
            score_parts.append(f"Score: **{question_scores[i]['score']}/10**")
        if i < len(el_scores):
            score_parts.append(f"Exec language: **{el_scores[i]}/10**")
        score_suffix = "  ·  " + " · ".join(score_parts) if score_parts else ""

        lines += [
            f"## Question {i+1} — {domain.title()}{score_suffix}",
            "",
            "### ❓ Question",
            "",
            question,
            "",
            "### 🗣 My Answer",
            "",
            "_[Skipped]_" if answer == "[SKIPPED]" else answer,
            "",
        ]

        details = fb.get("details", "")
        if details:
            lines += ["### 💡 Feedback (Details)", "", details, ""]

        ideal = fb.get("ideal", "")
        if ideal:
            lines += ["### ✨ Ideal Answer", "", ideal, ""]

        lines += ["---", ""]

    # Session summary table
    domain_averages = {
        d: round(sum(s) / len(s), 1) if s else 0
        for d, s in session.get("domain_scores", {}).items()
    }
    all_scores = session.get("question_scores", [])
    overall    = round(sum(q["score"] for q in all_scores) / len(all_scores), 1) if all_scores else 0

    el_raw = session.get("exec_lang_scores", [])
    try:
        el_avg = round(sum(float(s) for s in el_raw) / len(el_raw), 1) if el_raw else None
    except (ValueError, TypeError):
        el_avg = None

    lines += [
        "## Session Summary",
        "",
        f"**Overall: {overall}/10**",
        "",
        "| Category | Score |",
        "|----------|-------|",
    ]
    for d, avg in domain_averages.items():
        label = (d.replace("soft skills", "Soft Skills")
                  .replace("hard skills", "Hard Skills")
                  .replace("behavioural questions", "Behavioural"))
        lines.append(f"| {label} | {avg}/10 |")
    if el_avg is not None:
        lines.append(f"| Executive Language | {el_avg}/10 |")

    if final_feedback_text:
        lines += ["", "### Final Feedback", "", final_feedback_text.strip()]

    lines += ["", "---", "", "_Generated by Cara Coach_"]
    return "\n".join(lines)


# ── Session completion ────────────────────────────────────────────────────────
async def finish_session(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    session = sessions[chat_id]

    domain_averages = {
        d: round(sum(s) / len(s), 1) if s else 0
        for d, s in session["domain_scores"].items()
    }

    lang = session["settings"].get("lang", "en")

    all_scores = session["question_scores"]
    if all_scores:
        overall = round(sum(q["score"] for q in all_scores) / len(all_scores), 1)
        strongest = max(all_scores, key=lambda x: x["score"])
        weakest   = min(all_scores, key=lambda x: x["score"])
        strongest_line = f"💪 Strongest: \"{strongest['question'][:75]}…\" — {strongest['score']}/10"
        weakest_line   = f"📍 Weakest:   \"{weakest['question'][:75]}…\" — {weakest['score']}/10"
    else:
        overall = 0
        strongest_line = ""
        weakest_line   = ""

    el_scores = session.get("exec_lang_scores", [])
    try:
        el_avg = round(sum(float(s) for s in el_scores) / len(el_scores), 1) if el_scores else None
    except (ValueError, TypeError):
        el_avg = None

    # Build scores table (3 domain rows + exec language)
    score_rows = "\n".join(
        f"  {d.replace('soft skills','Soft skills').replace('hard skills','Hard skills').replace('behavioural questions','Behavioural'):<22}{avg}/10"
        for d, avg in domain_averages.items()
    )
    if el_avg is not None:
        score_rows += f"\n  {'Executive language':<22}{el_avg}/10"

    await context.bot.send_message(chat_id=chat_id, text=(
        f"🏁 SESSION COMPLETE\n\n"
        f"⭐ Overall: {overall}/10\n\n"
        f"📊 Scores:\n{score_rows}\n\n"
        f"{strongest_line}\n{weakest_line}"
    ))

    await context.bot.send_message(chat_id=chat_id, text="⏳ Preparing final feedback…")
    fb = await final_feedback(domain_averages, lang=lang)
    fb_clean = fb.replace('**', '').replace('*', '')
    await context.bot.send_message(chat_id=chat_id, text=f"💬 Final feedback:\n\n{fb_clean}")

    await context.bot.send_message(chat_id=chat_id, text="✅ Session complete! Good luck at the real interview 🚀")

    # Finalise session record (completed=True)
    update_session_snapshot(session, completed=True)

    # Generate and save Markdown export
    slug = session.get("slug", "")
    try:
        export_content  = generate_session_export(session, final_feedback_text=fb_clean)
        sid_safe        = session.get("session_start", "")[:19].replace(":", "").replace("T", "_")
        export_filename = f"export_{sid_safe}.md"
        export_path     = os.path.join(PROJECTS_DIR, slug, export_filename)
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(export_content)
        # Attach export_file reference to the history entry
        history_path = os.path.join(PROJECTS_DIR, slug, "session_history.json")
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
            sid = session.get("session_start", "")
            for h in history:
                if h.get("session_id") == sid:
                    h["export_file"] = export_filename
                    break
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        print(f"📄 Export saved: {export_path}")
    except Exception as e:
        print(f"⚠️ Export save failed: {e}")

    del sessions[chat_id]
    save_sessions(sessions)


# ── Bot startup ───────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    print("🤖 CaraCoachBot started! Press Ctrl+C to stop.")
    try:
        app.run_polling(drop_pending_updates=True)
    finally:
        cleanup_pid()


if __name__ == "__main__":
    main()
