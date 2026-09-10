"""
Integration tests for the Flask routes in app.py.

Run with:
    pytest
"""

import io
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import app as flask_app_module


@pytest.fixture
def client():
    flask_app_module.app.testing = True
    with flask_app_module.app.test_client() as c:
        yield c


def test_index_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<form" in resp.data


def test_screen_requires_jd(client):
    data = {
        "resume_files": (io.BytesIO(b"Skills: Python"), "candidate.txt"),
    }
    resp = client.post("/screen", data=data, content_type="multipart/form-data")
    # No JD provided -> redirected back to index with a flash message
    assert resp.status_code == 302


def test_screen_requires_resume(client):
    data = {"jd_text": "Requirements: Python, SQL."}
    resp = client.post("/screen", data=data, content_type="multipart/form-data")
    assert resp.status_code == 302


def test_screen_end_to_end(client):
    jd_text = "Requirements: 3+ years Python, SQL. Education: B.Tech."
    resume_text = b"Summary: 5 years experience in Python and SQL. B.Tech graduate."

    data = {
        "jd_text": jd_text,
        "resume_files": (io.BytesIO(resume_text), "candidate.txt"),
    }
    resp = client.post("/screen", data=data, content_type="multipart/form-data")

    assert resp.status_code == 200
    html = resp.data.decode()
    assert "candidate.txt" in html
    assert "Overall" in html or "overall" in html
