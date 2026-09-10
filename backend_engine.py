"""
backend_engine.py
------------------
All NLP / NER / matching / scoring logic lives here, as importable
functions and classes — no top-level execution. The Flask app (app.py)
imports from this module.

This is the same pipeline from the standalone script, refactored into a
library: Preprocessing -> Entity Extraction -> Structuring -> Matching ->
Scoring.
"""

import re
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict

import spacy
from spacy.matcher import PhraseMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------------------------
# Taxonomy / config — extend freely
# ---------------------------------------------------------------------------
SKILLS_TAXONOMY = [
    "python", "java", "c++", "sql", "nlp", "natural language processing",
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "scikit-learn", "spacy", "nltk", "data analysis", "data engineering",
    "pandas", "numpy", "aws", "azure", "gcp", "docker", "kubernetes",
    "airflow", "spark", "hadoop", "power bi", "tableau", "excel",
    "rest api", "flask", "django", "fastapi", "git", "linux",
    "computer vision", "opencv", "transformers", "llm", "generative ai",
    "statistics", "a/b testing", "etl", "mongodb", "postgresql", "mysql",
]

EDUCATION_KEYWORDS = [
    "b.tech", "btech", "b.e", "bachelor of engineering", "bachelor of science",
    "b.sc", "bca", "m.tech", "mtech", "master of science", "m.sc", "mca",
    "mba", "phd", "ph.d", "bachelor", "master", "doctorate",
]

EXPERIENCE_REGEX = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|year|yrs|yr)\b", re.IGNORECASE
)

# Matches with or without scheme/www, e.g. "github.com/jdoe" or
# "https://www.linkedin.com/in/jdoe". A leading scheme is added back if missing.
GITHUB_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.\-]+/?", re.IGNORECASE
)
LINKEDIN_REGEX = re.compile(
    r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/[A-Za-z0-9_.\-/%]+", re.IGNORECASE
)


def _normalize_url(raw: str) -> str:
    raw = raw.strip().rstrip(").,;")
    if not raw.lower().startswith("http"):
        raw = "https://" + raw
    return raw


def extract_github(text: str) -> str:
    m = GITHUB_REGEX.search(text)
    return _normalize_url(m.group(0)) if m else ""


def extract_linkedin(text: str) -> str:
    m = LINKEDIN_REGEX.search(text)
    return _normalize_url(m.group(0)) if m else ""

SECTION_WEIGHTS = {
    "skills": 0.45,
    "experience": 0.25,
    "education": 0.10,
    "summary": 0.20,
}

# ---------------------------------------------------------------------------
# NLP pipeline (loaded once, at import time)
# ---------------------------------------------------------------------------
nlp = spacy.blank("en")
nlp.add_pipe("sentencizer")

matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
matcher.add("SKILL", [nlp.make_doc(skill) for skill in SKILLS_TAXONOMY])


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------
def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Entity extraction ("NER" layer)
# ---------------------------------------------------------------------------
def extract_skills(doc_text: str) -> List[str]:
    doc = nlp(doc_text.lower())
    matches = matcher(doc)
    return sorted({doc[start:end].text for _, start, end in matches})


def extract_experience_years(doc_text: str) -> float:
    matches = EXPERIENCE_REGEX.findall(doc_text)
    years = [float(m) for m in matches]
    return max(years) if years else 0.0


def extract_education(doc_text: str) -> List[str]:
    text_lower = doc_text.lower()
    return sorted({kw for kw in EDUCATION_KEYWORDS if kw in text_lower})


def extract_summary(doc_text: str, max_sentences: int = 3) -> str:
    header_match = re.search(r"(summary|profile|objective)\s*[:\n]", doc_text, re.IGNORECASE)
    if header_match:
        start = header_match.end()
        snippet = doc_text[start:start + 600]
        cutoff = re.search(r"\n[A-Z][A-Za-z /]{2,25}\n", snippet)
        if cutoff:
            snippet = snippet[:cutoff.start()]
        return snippet.strip()

    doc = nlp(doc_text)
    sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
    return " ".join(sentences[:max_sentences])


# ---------------------------------------------------------------------------
# Structured record
# ---------------------------------------------------------------------------
@dataclass
class ParsedDocument:
    name: str
    raw_text: str
    skills: List[str] = field(default_factory=list)
    experience_years: float = 0.0
    education: List[str] = field(default_factory=list)
    summary: str = ""
    github: str = ""
    linkedin: str = ""

    def to_dict(self) -> Dict:
        d = asdict(self)
        d.pop("raw_text")
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def parse_document(name: str, text: str) -> ParsedDocument:
    text = clean_text(text)
    return ParsedDocument(
        name=name,
        raw_text=text,
        skills=extract_skills(text),
        experience_years=extract_experience_years(text),
        education=extract_education(text),
        summary=extract_summary(text),
        github=extract_github(text),
        linkedin=extract_linkedin(text),
    )


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------
def match_skills(jd_skills: List[str], resume_skills: List[str]) -> Dict:
    jd_set, res_set = set(jd_skills), set(resume_skills)
    matched = sorted(jd_set & res_set)
    missing = sorted(jd_set - res_set)
    extra = sorted(res_set - jd_set)
    score = (len(matched) / len(jd_set) * 100) if jd_set else 0.0
    return {"matched": matched, "missing": missing, "extra_in_resume": extra,
            "score_pct": round(score, 2)}


def match_experience(jd_years_required: float, resume_years: float) -> Dict:
    score = 100.0 if jd_years_required <= 0 else min(resume_years / jd_years_required, 1.0) * 100
    return {
        "required_years": jd_years_required,
        "candidate_years": resume_years,
        "meets_requirement": resume_years >= jd_years_required,
        "score_pct": round(score, 2),
    }


def match_education(jd_edu: List[str], resume_edu: List[str]) -> Dict:
    jd_set, res_set = set(jd_edu), set(resume_edu)
    if not jd_set:
        return {"matched": [], "missing": [], "score_pct": 100.0}
    matched = sorted(jd_set & res_set)
    missing = sorted(jd_set - res_set)
    return {"matched": matched, "missing": missing,
            "score_pct": round((len(matched) / len(jd_set)) * 100, 2)}


def match_summary(jd_summary: str, resume_summary: str) -> Dict:
    if not jd_summary.strip() or not resume_summary.strip():
        return {"score_pct": 0.0}
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform([jd_summary, resume_summary])
    sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
    return {"score_pct": round(sim * 100, 2)}


def build_report(jd: ParsedDocument, resume: ParsedDocument) -> Dict:
    skills_result = match_skills(jd.skills, resume.skills)
    exp_result = match_experience(jd.experience_years, resume.experience_years)
    edu_result = match_education(jd.education, resume.education)
    summ_result = match_summary(jd.summary, resume.summary)

    overall = (
        skills_result["score_pct"] * SECTION_WEIGHTS["skills"]
        + exp_result["score_pct"] * SECTION_WEIGHTS["experience"]
        + edu_result["score_pct"] * SECTION_WEIGHTS["education"]
        + summ_result["score_pct"] * SECTION_WEIGHTS["summary"]
    )

    return {
        "candidate": resume.name,
        "overall_match_pct": round(overall, 2),
        "sections": {
            "skills": skills_result,
            "experience": exp_result,
            "education": edu_result,
            "summary": summ_result,
        },
    }


# ---------------------------------------------------------------------------
# File text extraction (txt / pdf / docx) — used by the Flask upload route
# ---------------------------------------------------------------------------
def extract_text_from_file(filepath: str) -> str:
    lower = filepath.lower()
    if lower.endswith(".pdf"):
        import pdfplumber
        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    elif lower.endswith(".docx"):
        import docx
        d = docx.Document(filepath)
        return "\n".join(p.text for p in d.paragraphs)
    else:  # .txt or anything else — read as plain text
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def screen_resumes(jd_text: str, resume_entries: List[Dict]) -> List[Dict]:
    """
    Main entry point the Flask route calls.

    jd_text: raw JD text (already extracted from its upload)
    resume_entries: list of dicts, each {"path": <stored filepath>,
                     "original_name": <candidate-facing filename>}

    Returns (jd_summary_dict, reports) where reports is ranked by
    overall_match_pct descending. Each report includes:
      - candidate, overall_match_pct, sections{...}, parsed{...}
      - stored_filename  -> use to build a download/view link for the resume
      - matched_summary / not_matched_summary -> combined skills+education
        remarks text, ready to drop straight into a table cell ("-" if empty)
    """
    jd_doc = parse_document("Job_Description", jd_text)

    reports = []
    for entry in resume_entries:
        filepath = entry["path"]
        candidate_name = entry.get("original_name") or filepath.split("/")[-1]

        text = extract_text_from_file(filepath)
        resume_doc = parse_document(candidate_name, text)
        report = build_report(jd_doc, resume_doc)
        report["parsed"] = resume_doc.to_dict()
        report["stored_filename"] = filepath.split("/")[-1]

        matched_items = (
            report["sections"]["skills"]["matched"]
            + report["sections"]["education"]["matched"]
        )
        missing_items = (
            report["sections"]["skills"]["missing"]
            + report["sections"]["education"]["missing"]
        )
        report["matched_summary"] = ", ".join(matched_items) if matched_items else "-"
        report["not_matched_summary"] = ", ".join(missing_items) if missing_items else "-"

        reports.append(report)

    reports.sort(key=lambda r: r["overall_match_pct"], reverse=True)
    jd_summary_for_ui = jd_doc.to_dict()
    return jd_summary_for_ui, reports
