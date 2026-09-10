# Contributing

Thanks for considering a contribution!

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/resume-screening-app.git
cd resume-screening-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Before opening a pull request

1. Add or update tests in `tests/` for any behavior change.
2. Run the full suite: `pytest -v` — it must pass.
3. Keep `backend_engine.py` framework-agnostic (no Flask imports) so it stays reusable outside the web app.
4. If you change scoring behavior (weights, thresholds), call it out clearly in the PR description since it changes ranking results for existing users.

## Reporting issues

Open a GitHub issue with:
- What you expected vs. what happened
- A minimal JD/resume text sample that reproduces it (redact any real personal data)
- Python version and OS
