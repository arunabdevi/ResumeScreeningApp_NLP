# Resume Screening App

A resume-to-job-description matcher built with NLP / rule-based NER techniques. Upload a job description and one or more resumes, and get a ranked, section-wise match score (skills, experience, education, summary) with matched/not-matched detail for each candidate — via a Flask web UI.

![Tests](https://github.com/YOUR_USERNAME/resume-screening-app/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> Replace `YOUR_USERNAME` above once this is pushed to your own GitHub account, so the badge points at your repo's Actions runs.

---

## Features

- **JD vs. resume matching** across four sections: skills, experience, education, and summary
- **Rule-based NER** for skill extraction via a spaCy `PhraseMatcher` against a configurable skills taxonomy — no large model download required
- **GitHub / LinkedIn link extraction** from resume text
- **Weighted overall score** (weights are configurable in one place)
- **Web UI**: upload JD (paste or file) + multiple resumes (`.txt`, `.pdf`, `.docx`), get a ranked results table with per-section scores and matched/not-matched remarks
- **Resume viewer link** — each row links back to the candidate's original uploaded file
- Fully offline / no external API calls — safe to run on sensitive candidate data in a private environment

---

## Architecture

```
                 ┌────────────────────┐
                 │   Flask front end    │
                 │  (app.py + templates)│
                 └─────────┬───────────┘
                           │  JD text/file + resume files
                           ▼
                 ┌────────────────────┐
                 │  File extraction    │  .txt / .pdf (pdfplumber) / .docx (python-docx)
                 └─────────┬───────────┘
                           ▼
                 ┌────────────────────┐
                 │   Preprocessing     │  clean_text()
                 └─────────┬───────────┘
                           ▼
                 ┌────────────────────┐
                 │  Entity extraction  │  spaCy PhraseMatcher (skills) +
                 │   ("NER" layer)     │  regex (experience, GitHub, LinkedIn) +
                 │                     │  keyword match (education) +
                 │                     │  header/sentence heuristic (summary)
                 └─────────┬───────────┘
                           ▼
                 ┌────────────────────┐
                 │ Structured record   │  ParsedDocument dataclass -> JSON
                 └─────────┬───────────┘
                           ▼
                 ┌────────────────────┐
                 │  Matching engine    │  per-section comparators
                 │  (skills/exp/edu/   │  (Jaccard overlap, numeric threshold,
                 │   summary)          │   keyword overlap, TF-IDF cosine sim)
                 └─────────┬───────────┘
                           ▼
                 ┌────────────────────┐
                 │  Weighted scoring   │  SECTION_WEIGHTS -> overall_match_pct
                 └─────────┬───────────┘
                           ▼
                 ┌────────────────────┐
                 │  Ranked report      │  rendered as an HTML table
                 └────────────────────┘
```

All of the extraction/matching/scoring logic lives in `backend_engine.py` and is fully decoupled from Flask — you can `import backend_engine` and use it from a script, a notebook, or a different web framework entirely.

---

## Project structure

```
resume-screening-app/
├── app.py                    # Flask routes: GET /, POST /screen, GET /uploads/<file>
├── backend_engine.py          # NLP/NER extraction, matching, scoring (framework-agnostic)
├── requirements.txt            # runtime dependencies
├── requirements-dev.txt        # runtime + pytest
├── .env.example                # template for local environment variables
├── templates/
│   ├── index.html              # upload form
│   └── results.html            # ranked results table + detailed breakdown
├── static/
│   └── style.css
├── uploads/                    # runtime storage for uploaded resumes (gitignored)
├── tests/
│   ├── test_backend_engine.py  # unit tests for extraction/matching/scoring
│   └── test_app.py             # Flask route integration tests
├── .github/workflows/tests.yml # CI: runs pytest on push/PR across Python 3.10–3.12
├── .gitignore
├── LICENSE
└── README.md
```

---

## Getting started

### 1. Clone and enter the project
```bash
git clone https://github.com/YOUR_USERNAME/resume-screening-app.git
cd resume-screening-app
```

### 2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```
(For running tests too: `pip install -r requirements-dev.txt`)

### 4. Configure environment variables (optional but recommended)
```bash
cp .env.example .env
```
Then edit `.env` and set a real `FLASK_SECRET_KEY`. `app.py` reads it via `os.environ.get(...)` with a dev fallback, so this step is optional for local testing but required before any real deployment.

### 5. Run the app
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser.

### 6. Use it
1. Paste the job description text, or upload a JD file (`.txt`/`.pdf`/`.docx`).
2. Upload one or more resumes.
3. Click **Screen Resumes**.
4. Review the ranked table: per-section scores, overall %, GitHub/LinkedIn/resume links, and matched vs. not-matched remarks (missing data shows as `-`).

---

## Running tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

Tests cover:
- Extraction functions (skills, experience years, education, GitHub/LinkedIn, summary)
- Matching functions (skills overlap, experience threshold, education overlap, summary similarity)
- End-to-end Flask routes (form load, validation, full screen → results flow)

CI (`.github/workflows/tests.yml`) runs this same suite automatically on every push and pull request against Python 3.10, 3.11, and 3.12.

---

## Configuration

All matching behavior is centralized in `backend_engine.py`:

| What to change | Where |
|---|---|
| Skills vocabulary | `SKILLS_TAXONOMY` list |
| Education keywords | `EDUCATION_KEYWORDS` list |
| Section weighting for overall score | `SECTION_WEIGHTS` dict |
| Allowed upload file types | `ALLOWED_EXTENSIONS` in `app.py` |
| Max upload size | `MAX_CONTENT_LENGTH` in `app.py` |

---

## Roadmap / possible upgrades

- Swap the TF-IDF summary similarity for `sentence-transformers` embeddings for stronger semantic matching
- Replace the `PhraseMatcher` skill extraction with a trained spaCy NER model once labeled resume data is available
- Fuzzy-match skill variants (e.g. "ML" vs. "machine learning") with `rapidfuzz`
- Add authentication and rate limiting before exposing this beyond local/internal use
- Add a scheduled cleanup job for `uploads/` (files currently persist so the "View resume" links keep working — see `app.py`)

---

## License

MIT — see [LICENSE](LICENSE).
