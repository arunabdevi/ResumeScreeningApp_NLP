"""
app.py — Flask front end for the resume screening backend.

Routes:
    GET  /            -> upload form (JD text/file + multiple resume files)
    POST /screen       -> runs the pipeline, renders results.html

Run:
    python app.py
Then open:
    http://127.0.0.1:5000
"""

import os
import uuid
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename

import backend_engine as engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload cap


def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/screen", methods=["POST"])
def screen():
    # --- 1. Get JD text: either pasted text or an uploaded JD file ---
    jd_text = request.form.get("jd_text", "").strip()
    jd_file = request.files.get("jd_file")

    if jd_file and jd_file.filename and allowed_file(jd_file.filename):
        jd_path = os.path.join(UPLOAD_DIR, f"jd_{uuid.uuid4().hex}_{jd_file.filename}")
        jd_file.save(jd_path)
        jd_text = engine.extract_text_from_file(jd_path)

    if not jd_text:
        flash("Please paste the JD text or upload a JD file.")
        return redirect(url_for("index"))

    # --- 2. Get resume files (multiple) ---
    resume_files = request.files.getlist("resume_files")
    resume_entries = []
    for f in resume_files:
        if f and f.filename and allowed_file(f.filename):
            original_name = secure_filename(f.filename)
            stored_name = f"res_{uuid.uuid4().hex}_{original_name}"
            path = os.path.join(UPLOAD_DIR, stored_name)
            f.save(path)
            resume_entries.append({"path": path, "original_name": original_name})

    if not resume_entries:
        flash("Please upload at least one resume (.txt, .pdf, or .docx).")
        return redirect(url_for("index"))

    # --- 3. Run the NLP/NER + matching + scoring pipeline ---
    jd_parsed, reports = engine.screen_resumes(jd_text, resume_entries)

    # --- 4. Build a viewable link for each candidate's resume file ---
    # Files are kept in UPLOAD_DIR (not deleted) so this link stays valid
    # for the rest of the session. Add a periodic cleanup job in production.
    for r in reports:
        r["resume_url"] = url_for("serve_resume", filename=r["stored_filename"])

    return render_template("results.html", jd=jd_parsed, reports=reports)


@app.route("/uploads/<path:filename>")
def serve_resume(filename):
    # send_from_directory guards against path traversal outside UPLOAD_DIR
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    # debug=True auto-reloads on code changes — turn off in production
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)
