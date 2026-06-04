import anthropic
import subprocess

NUM_QUESTIONS = 6
DOMAIN1 = "soft skills"
DOMAIN2 = "hard skills"
DOMAIN3 = "behavioural questions"

key = subprocess.run(
    ["security", "find-generic-password", "-a", subprocess.getoutput("whoami"), "-s", "ANTHROPIC_API_KEY", "-w"],
    capture_output=True, text=True
).stdout.strip()

async_client = anthropic.AsyncAnthropic(api_key=key)

async def ask_claude_async(prompt):
    """Async — используется в Telegram bot, не блокирует event loop."""
    response = await async_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def ingest_cv_jd(cv_path, jd_path):
    cv_text = ""
    for enc in ("utf-8", "utf-16", "latin-1", "cp1252"):
        try:
            with open(cv_path, "r", encoding=enc) as f:
                cv_text = f.read()
            break
        except (UnicodeDecodeError, ValueError):
            continue

    with open(jd_path, "r", encoding="utf-8", errors="ignore") as f:
        jd_text = f.read()
    return cv_text, jd_text

async def analyze_gaps(cv_text, jd_text, lang="en"):
    lang_instruction = "Respond in English." if lang == "en" else "Отвечай на русском языке."
    prompt = (
        f"Compare the CV and job description, identify gaps and give recommendations.\n\n"
        f"CV:\n{cv_text}\n\nJob Description:\n{jd_text}\n\n{lang_instruction}"
    )
    return await ask_claude_async(prompt)

async def generate_questions(gaps, lang="en"):
    questions_per_domain = max(1, NUM_QUESTIONS // 3)
    lang_instruction = "Write all questions in English." if lang == "en" else "Пиши все вопросы на русском языке."
    prompt = (
        f"Generate interview questions based on the candidate's gaps.\n\n"
        f"Gaps:\n{gaps}\n\n"
        f"Divide into 3 categories, {questions_per_domain} question(s) each:\n"
        f"- {DOMAIN1}: communication, leadership, teamwork, empathy, adaptability\n"
        f"- {DOMAIN2}: technical knowledge, tools, methodologies, AI/ML, platforms\n"
        f"- {DOMAIN3}: specific past situations using STAR method\n\n"
        f"STRICT format (no extra text):\n\n"
        f"{DOMAIN1}:\n1. [write a real soft skills question]\n\n"
        f"{DOMAIN2}:\n1. [write a real hard skills question]\n\n"
        f"{DOMAIN3}:\n1. [write a real behavioural question]\n\n"
        f"Each question must be specific, detailed and realistic for a real interview. "
        f"Do NOT write the word 'question' as the question text.\n\n"
        f"{lang_instruction}"
    )
    raw = await ask_claude_async(prompt)

    # парсим в словарь {domain: [вопросы]}
    result = {DOMAIN1: [], DOMAIN2: [], DOMAIN3: []}
    current_domain = None
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # убираем markdown символы перед проверкой домена
        clean_line = line.strip("*#:").strip().lower()
        matched_domain = next((d for d in result if clean_line.startswith(d.lower())), None)
        if matched_domain:
            current_domain = matched_domain
        elif current_domain and line[0].isdigit():
            question = line.split(".", 1)[-1].strip()
            result[current_domain].append(question)
    return result

async def extract_cv_catalog(cv_text, jd_text, lang="en"):
    """One-time extraction: structured story catalog from full CV, targeted at the specific JD.
    Cached and reused for every question — replaces sending the full CV each time."""
    lang_instruction = "Respond in English." if lang == "en" else "Отвечай на русском языке."
    prompt = (
        f"You are preparing a candidate for a specific job interview.\n"
        f"Extract a structured story catalog from their CV, relevant to the job description.\n"
        f"Be thorough — do not skip any role or achievement.\n\n"
        f"Job Description:\n{jd_text}\n\n"
        f"CV:\n{cv_text}\n\n"
        f"Return EXACTLY in this format (plain text only, no markdown, no asterisks):\n\n"
        f"ROLES:\n"
        f"[Every role without exception — one per line: Title | Company | Dates]\n\n"
        f"TOP STORIES:\n"
        f"[12 specific behavioral interview stories. Each on one line:\n"
        f"Theme | Company, Year | Situation in 1 sentence → What candidate did → Result with number or outcome\n"
        f"Cover all these themes: leadership, conflict, failure, innovation, "
        f"stakeholder management, crisis, team scale, strategic decision, "
        f"cross-functional work, customer impact, product delivery, process improvement]\n\n"
        f"KEY METRICS:\n"
        f"[Every number, percentage, team size, budget, timeline from the CV — none skipped]\n\n"
        f"DOMAINS:\n"
        f"[All industries and domains the candidate has worked in]\n\n"
        f"STRONGEST MATCH:\n"
        f"[Top 5 specific CV points that directly match this job description — be concrete]\n\n"
        f"{lang_instruction}"
    )
    return await ask_claude_async(prompt)


def analyze_speech(answer):
    """Analyses answer text: filler words, length, pace."""
    words = answer.split()
    word_count = len(words)

    # Estimate duration (average speech ~120 words/min)
    duration_sec = round(word_count / 120 * 60)

    # Filler words (Russian and English)
    fillers_ru = {"ну", "это", "вот", "короче", "типа", "значит", "как бы", "в общем", "собственно", "буквально"}
    fillers_en = {"like", "you know", "basically", "actually", "literally", "so", "um", "uh", "right"}
    all_fillers = fillers_ru | fillers_en

    found_fillers = []
    text_lower = answer.lower()
    for filler in all_fillers:
        count = text_lower.split().count(filler)
        if count >= 2:
            found_fillers.append(f'"{filler}" ({count}x)')

    # Speech pace
    if word_count / max(duration_sec, 1) * 60 < 90:
        tempo = f"⚠️ Speech pace: ~{duration_sec}s — too slow, may sound uncertain"
    elif word_count / max(duration_sec, 1) * 60 > 160:
        tempo = f"⚠️ Speech pace: ~{duration_sec}s — too fast, hard to follow"
    else:
        tempo = f"✅ Speech pace: ~{duration_sec}s — good pace"

    # Answer length
    if duration_sec < 30:
        length = f"⚠️ Answer length: ~{duration_sec}s — too short"
    elif duration_sec > 120:
        length = f"⚠️ Answer length: ~{duration_sec}s — too long, focus on the key points"
    else:
        length = f"✅ Answer length: ~{duration_sec}s — optimal"

    # Filler words
    if found_fillers:
        fillers_line = f"⚠️ Filler words: {', '.join(found_fillers)}"
    else:
        fillers_line = "✅ Filler words: none detected"

    return f"{tempo}\n{fillers_line}\n{length}"


def _build_score_prompt(question, answer, cv_text, mode, lang):
    """Builds the prompt for score_and_ideal. Shared by streaming and non-streaming versions."""
    is_mirror = mode.lower() == "mirror"
    if is_mirror:
        style = "Be direct and uncompromising. No softening. Name weaknesses plainly. The candidate wants brutally honest feedback."
    else:
        style = "Be honest but supportive. Highlight strengths, then point out specifically what to improve. Warm but honest tone."
    lang_instruction = "Respond in English." if lang == "en" else "Отвечай на русском языке."

    exec_lang_format = (
        f"EXEC_LANG_SCORE: [float 1.0–10.0 with one decimal — rate HOW the answer is delivered, "
        f"not what was said. Score is independent of content quality. "
        f"Evaluate only the applicable parameters below:\n"
        f"(1) TOP-DOWN STRUCTURE [always applies]: Does the answer lead with the main point, "
        f"then support with details? Score lower if the conclusion arrives only after 3+ sentences of context.\n"
        f"(2) HEDGING DENSITY [always applies]: Frequency of uncertainty markers relative to answer length — "
        f"'I think', 'maybe', 'sort of', 'kind of', 'I guess', 'probably', 'hopefully', 'I'm not sure'. "
        f"One hedge in a long answer = acceptable. High density = penalise.\n"
        f"(3) APOLOGY LANGUAGE DENSITY [always applies]: Frequency of apology phrases relative to answer length — "
        f"'sorry if this is too long', 'I don't know if I'm answering correctly', 'I hope that makes sense'. "
        f"Evaluate as density, not absolute count.\n"
        f"(4) RESULT PRESENCE [question-aware — skip if question is about process, preference, or opinion]: "
        f"If the question implies a past action, project, decision, or achievement — does the answer include "
        f"a result (quantitative OR qualitative)? Penalise only if result is expected but absent.\n"
        f"(5) PROFESSIONAL VOCABULARY [always applies]: Does the speaker use domain-appropriate terminology, "
        f"or describe things vaguely? Score higher for natural correct use of professional terms. "
        f"Score lower for vague replacements ('those little chart things' vs 'Gantt chart').\n"
        f"(6) PATTERN & FRAMEWORK THINKING [question-aware — skip if question is about a specific past event]: "
        f"If the question asks about approach, process, or methodology — does the speaker generalise into "
        f"a repeatable framework, or only narrate one specific instance? "
        f"Score higher when a method is demonstrated and an example illustrates it.\n"
        f"Exclude inapplicable parameters (4, 6) from the score calculation — do not penalise for their absence.]"
    )

    exec_lang_feedback_format = (
        f"\nEXEC_LANG_FEEDBACK: [1-2 specific verbatim quotes from the candidate's answer above "
        f"that show weak executive language, each with a rewrite. "
        f"Use EXACTLY this format for each example:\n"
        f"You said: \"[exact quote from answer]\"\n"
        f"Try instead: \"[rewritten in senior executive register]\"\n"
        f"If the answer has no weak language patterns, write: none]"
    )

    return (
        f"You are an experienced recruiter and career coach.\n\n"
        f"Evaluation style: {style}\n\n"
        f"IMPORTANT: this is a transcription of live speech — ignore typos, grammar, spelling. "
        f"Evaluate only the meaning and content.\n\n"
        f"Question: {question}\n"
        f"Candidate's answer: {answer}\n\n"
        f"Candidate's experience catalog (use real stories and metrics from it for the ideal answer):\n{cv_text}\n\n"
        f"{lang_instruction}\n\n"
        f"Return STRICTLY in this format. Plain text only — no markdown, no asterisks, no italic, no bold:\n\n"
        f"SCORE: [number from 1 to 10]\n"
        f"SUMMARY: [one sentence — overall impression and reason for score]\n"
        f"POSITIVE_TITLE: [short title of the strength]\n"
        f"POSITIVE_BODY: [2-3 sentences on what specifically worked]\n"
        f"FLAG_TITLE: [short title of the main weakness]\n"
        f"FLAG_BODY: [2-3 sentences on what was missing or weak]\n"
        f"IMPROVE: [3-4 specific tips numbered (1) (2) (3) (4) — plain text, no markdown]\n"
        f"STAR_TIP: [one specific tip on how to apply STAR to this answer]\n"
        f"IDEAL: [ideal answer — as an experienced senior candidate would answer, "
        f"based ONLY on real past experience from the CV above. "
        f"IMPORTANT: the candidate is APPLYING for this role — do NOT invent experience at the target company, "
        f"do NOT claim they already work there or have insider knowledge of it. "
        f"Use STAR structure where appropriate, 5-8 sentences, maximum 130 words, "
        f"(Situation 1-2 sentences → Action 2-3 sentences → Result 1-2 sentences), "
        f"natural confident speech, plain text only, no markdown]\n"
        f"{exec_lang_format}"
        f"{exec_lang_feedback_format}"
    )


def _parse_score_raw(raw, answer, previous_score):
    """Parses Claude's structured response. Shared by streaming and non-streaming."""
    def extract(key):
        for line in raw.split("\n"):
            if line.startswith(f"{key}:"):
                return line[len(key)+1:].strip()
        return ""

    ALL_KEYS = [
        "SCORE", "SUMMARY", "POSITIVE_TITLE", "POSITIVE_BODY",
        "FLAG_TITLE", "FLAG_BODY", "IMPROVE", "STAR_TIP",
        "IDEAL", "EXEC_LANG_SCORE", "EXEC_LANG_FEEDBACK",
    ]

    def extract_multiline(key):
        lines = raw.split("\n")
        result = []
        capturing = False
        for line in lines:
            if line.startswith(f"{key}:"):
                result.append(line[len(key)+1:].strip())
                capturing = True
            elif capturing:
                if any(line.startswith(f"{k}:") for k in ALL_KEYS):
                    break
                result.append(line)
        return "\n".join(result).strip()

    score_num          = extract("SCORE")
    summary            = extract("SUMMARY")
    pos_title          = extract("POSITIVE_TITLE")
    pos_body           = extract_multiline("POSITIVE_BODY")
    flag_title         = extract("FLAG_TITLE")
    flag_body          = extract_multiline("FLAG_BODY")
    improve            = extract_multiline("IMPROVE")
    star_tip           = extract("STAR_TIP")
    ideal              = extract_multiline("IDEAL")
    exec_lang_score    = extract("EXEC_LANG_SCORE")
    exec_lang_feedback = extract_multiline("EXEC_LANG_FEEDBACK")
    speech             = analyze_speech(answer)

    try:
        score_int = int(score_num)
    except (ValueError, TypeError):
        score_int = None

    if previous_score is not None and score_int is not None:
        delta = score_int - previous_score
        if delta > 0:
            score_header = f"📈 Score: {score_num}/10 (+{delta})"
        elif delta < 0:
            score_header = f"📉 Score: {score_num}/10 ({delta})"
        else:
            score_header = f"➡️ Score: {score_num}/10 (no change)"
    else:
        score_header = f"🌟 Score: {score_num}/10"

    return (score_num, score_header, summary, pos_title, pos_body,
            flag_title, flag_body, improve, star_tip, speech, ideal,
            exec_lang_score, exec_lang_feedback)


async def ask_claude_async_stream(prompt):
    """Async generator — yields text chunks as Claude streams them."""
    async with async_client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        async for text in stream.text_stream:
            yield text



async def final_feedback(domain_averages, lang="en"):
    summary = "\n".join(f"{domain}: {avg}/10" for domain, avg in domain_averages.items())
    lang_instruction = "Respond in English." if lang == "en" else "Отвечай на русском языке."
    prompt = (
        f"Candidate's interview scores:\n{summary}\n\n"
        f"Write a SHORT, punchy debrief. Maximum 120 words total. No filler, no repetition.\n\n"
        f"Use EXACTLY this structure:\n\n"
        f"WHAT'S WORKING:\n"
        f"- [1-2 specific strengths based on the scores]\n\n"
        f"TOP 3 TO IMPROVE:\n"
        f"1. [specific and actionable — one sentence]\n"
        f"2. [specific and actionable — one sentence]\n"
        f"3. [specific and actionable — one sentence]\n\n"
        f"FOCUS FOR NEXT SESSION:\n"
        f"[ONE concrete thing to practice before the next interview — one sentence]\n\n"
        f"Be direct. No generic advice. No encouraging fluff. Plain text only.\n"
        f"{lang_instruction}"
    )
    return await ask_claude_async(prompt)

if __name__ == "__main__":
    print("cara_agent.py — library module, not meant to be run directly.")
    print("Use bot.py to start the Telegram bot.")
