from flask import Flask, render_template, request, jsonify, send_file
import os
import re
import json
import docx

app = Flask(__name__, template_folder="frontend")

PROJECTS_DIR = "projects"
CV_FILE      = "my_cv.txt"


# ── Helpers ────────────────────────────────────────────────────────────────────
def make_slug(company, role):
    s = f"{company}_{role}".lower().strip()
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^a-z0-9_]', '', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s[:60] or "project"


def list_projects():
    projects = []
    if not os.path.exists(PROJECTS_DIR):
        return projects
    for slug in sorted(os.listdir(PROJECTS_DIR)):
        path = os.path.join(PROJECTS_DIR, slug, "settings.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                s = json.load(f)
            s["slug"]      = slug
            s["has_cache"] = os.path.exists(os.path.join(PROJECTS_DIR, slug, "cached_analysis.json"))
            # Дата последней сессии для сортировки
            history_path = os.path.join(PROJECTS_DIR, slug, "session_history.json")
            if os.path.exists(history_path):
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                s["last_session"] = max((h.get("session_id", "") for h in history), default="")
            else:
                s["last_session"] = ""
            projects.append(s)
    # Сортируем: у кого последняя сессия позже — тот первый; без сессий — в конец
    projects.sort(key=lambda p: p["last_session"] or "0000", reverse=True)
    return projects



# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
@app.route("/start")
def start():
    projects = list_projects()
    has_cv   = os.path.exists(CV_FILE)
    return render_template("cara-light-organic.html", projects=projects, has_cv=has_cv)


@app.route("/api/projects")
def api_projects():
    return jsonify(list_projects())


@app.route("/api/sessions/<slug>")
def api_sessions(slug):
    path = os.path.join(PROJECTS_DIR, slug, "session_history.json")
    if not os.path.exists(path):
        return jsonify([])
    with open(path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/submit", methods=["POST"])
def submit():
    role    = request.form.get("role", "")
    company = request.form.get("company", "")
    jd      = request.form.get("jd", "")
    lang    = request.form.get("lang", "en")
    date    = request.form.get("date", "")
    mode    = request.form.get("mode", "coach")
    slug    = request.form.get("slug", "").strip()
    cv_file = request.files.get("cv")

    if not slug:
        slug = make_slug(company, role)

    project_dir = os.path.join(PROJECTS_DIR, slug)
    os.makedirs(project_dir, exist_ok=True)

    # CV — shared for all projects
    cv_changed = False
    if cv_file and cv_file.filename:
        cv_changed = True
        filename = cv_file.filename.lower()
        if filename.endswith(".docx"):
            cv_file.save("my_cv_temp.docx")
            doc  = docx.Document("my_cv_temp.docx")
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            with open(CV_FILE, "w", encoding="utf-8") as f:
                f.write(text)
            os.remove("my_cv_temp.docx")
        else:
            cv_file.save(CV_FILE)

    # Settings per project — preserve existing status and detect lang change before overwriting
    existing_settings_path = os.path.join(project_dir, "settings.json")
    existing_status = "active"
    existing_lang   = None
    if os.path.exists(existing_settings_path):
        try:
            with open(existing_settings_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                existing_status = existing.get("status", "active")
                existing_lang   = existing.get("lang")
        except Exception:
            pass

    lang_changed = existing_lang is not None and existing_lang != lang

    settings = {
        "role": role, "company": company, "jd": jd,
        "lang": lang, "date": date, "mode": mode, "slug": slug,
        "status": existing_status,
    }
    with open(existing_settings_path, "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

    # Invalidate cache if JD, CV, or interview language changed
    jd_path    = os.path.join(project_dir, "jd.txt")
    cache_path = os.path.join(project_dir, "cached_analysis.json")

    jd_changed = True
    if os.path.exists(jd_path):
        with open(jd_path, "r", encoding="utf-8") as f:
            jd_changed = f.read().strip() != jd.strip()

    # Write new JD
    with open(jd_path, "w", encoding="utf-8") as f:
        f.write(jd)

    if (jd_changed or cv_changed or lang_changed) and os.path.exists(cache_path):
        os.remove(cache_path)
        reason = []
        if jd_changed:   reason.append("JD changed")
        if cv_changed:   reason.append("CV changed")
        if lang_changed: reason.append(f"language changed ({existing_lang} → {lang})")
        print(f"🗑 Cache invalidated for {slug} ({', '.join(reason)})")

    print(f"✅ Project saved: {slug}")
    return jsonify({"status": "ok", "slug": slug})


@app.route("/api/projects/<slug>/export/range")
def export_range(slug):
    import re
    date_from = request.args.get("from", "")
    date_to   = request.args.get("to", "")
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_from) or not re.match(r'^\d{4}-\d{2}-\d{2}$', date_to):
        return jsonify({"error": "invalid date format"}), 400
    if date_from > date_to:
        return jsonify({"error": "from must be <= to"}), 400

    history_path = os.path.join(PROJECTS_DIR, slug, "session_history.json")
    if not os.path.exists(history_path):
        return jsonify({"error": "no sessions"}), 404
    with open(history_path, "r", encoding="utf-8") as f:
        history = json.load(f)

    sessions_in_range = [
        s for s in history
        if s.get("completed") and date_from <= s.get("date", "") <= date_to
    ]
    if not sessions_in_range:
        return jsonify({"error": "no completed sessions in this range"}), 404

    sessions_in_range.sort(key=lambda s: s.get("session_id", ""))

    settings_path = os.path.join(PROJECTS_DIR, slug, "settings.json")
    role, company = "—", "—"
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            st = json.load(f)
        role    = st.get("role", "—")
        company = st.get("company", "—")

    date_label = date_from if date_from == date_to else f"{date_from} — {date_to}"
    lines = [
        f"# Interview Export — {role} at {company}",
        "",
        f"**Period:** {date_label}",
        f"**Sessions:** {len(sessions_in_range)}",
        "",
        "---",
        "",
    ]

    for i, sess in enumerate(sessions_in_range, 1):
        sid      = sess.get("session_id", "")
        date_str = sid[:10]
        time_str = sid[11:16] if len(sid) > 10 else ""
        export_f = sess.get("export_file")
        overall  = sess.get("overall", "—")
        da       = sess.get("domain_averages", {})
        el       = sess.get("exec_lang_avg")
        retried  = sess.get("retry_count", 0)

        lines += [f"# Session {i} — {date_str} {time_str}", ""]

        if export_f:
            exp_path = os.path.join(PROJECTS_DIR, slug, export_f)
            if os.path.exists(exp_path):
                with open(exp_path, encoding="utf-8") as f:
                    content = f.read()
                content_lines = content.split("\n")
                try:
                    sep_idx = content_lines.index("---")
                    body    = "\n".join(content_lines[sep_idx + 1:])
                except ValueError:
                    body = content
                lines.append(body)
            else:
                lines += [f"> ⚠️ Export file not found: {export_f}", ""]
        else:
            lines += [
                "> ⚠️ Full transcript not available — session completed before export was introduced.",
                "",
                "## Session Summary",
                "",
                f"**Overall: {overall}/10**",
                f"**Retried:** {retried}",
                "",
                "| Category | Score |",
                "|----------|-------|",
            ]
            for d, avg in da.items():
                label = (d.replace("soft skills", "Soft Skills")
                          .replace("hard skills", "Hard Skills")
                          .replace("behavioural questions", "Behavioural"))
                lines.append(f"| {label} | {avg}/10 |")
            if el is not None:
                lines.append(f"| Executive Language | {el}/10 |")
            lines += ["", "---", ""]

    lines += ["", "---", "", "_Generated by Cara Coach_"]
    output   = "\n".join(lines)
    filename = f"export_{date_from}_{date_to}.md" if date_from != date_to else f"export_{date_from}.md"

    from io import BytesIO
    buf = BytesIO(output.encode("utf-8"))
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="text/markdown")


@app.route("/api/projects/<slug>/export/<filename>")
def download_export(slug, filename):
    # Safety: only allow export_*.md files from the project directory
    if not filename.startswith("export_") or not filename.endswith(".md"):
        return jsonify({"error": "invalid file"}), 400
    path = os.path.join(PROJECTS_DIR, slug, filename)
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404
    return send_file(path, as_attachment=True, download_name=filename, mimetype="text/markdown")


@app.route("/api/projects/<slug>/status", methods=["POST"])
def set_project_status(slug):
    data   = request.get_json(force=True)
    status = data.get("status", "")
    if status not in ("closed", "active"):
        return jsonify({"error": "invalid status"}), 400
    path = os.path.join(PROJECTS_DIR, slug, "settings.json")
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404
    with open(path, "r", encoding="utf-8") as f:
        settings = json.load(f)
    settings["status"] = status
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True, "slug": slug, "status": status})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
