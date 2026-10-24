"""API integration and route tests for Redline Flask application."""

import io
from pathlib import Path
import pytest
from app import create_app

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Redline" in response.data
    assert b"Submission" in response.data


def test_health_check_route(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["app"] == "Redline AI Resume Analyzer"


def test_analyze_missing_job_description(client):
    response = client.post("/api/analyze", data={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == "EMPTY_JOB_DESCRIPTION"


def test_analyze_job_description_too_short(client):
    response = client.post("/api/analyze", data={
        "job_description": "We need a python dev who knows flask and sql."  # only 10 words
    })
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == "JD_TOO_SHORT"
    assert "at least 40 words" in data["error"]


def test_analyze_missing_file(client):
    sample_jd = (
        "We are looking for an experienced senior software engineer who has deep expertise "
        "in Python, Flask, FastAPI, PostgreSQL, and cloud deployments with Docker and Kubernetes. "
        "You will design scalable architectures, participate in code reviews, and drive engineering excellence. "
        "Strong communication, problem solving, and leadership skills are required for this position."
    )
    response = client.post("/api/analyze", data={"job_description": sample_jd})
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == "NO_FILE_UPLOADED"


def test_analyze_invalid_extension(client):
    sample_jd = (
        "We are looking for an experienced senior software engineer who has deep expertise "
        "in Python, Flask, FastAPI, PostgreSQL, and cloud deployments with Docker and Kubernetes. "
        "You will design scalable architectures, participate in code reviews, and drive engineering excellence. "
        "Strong communication, problem solving, and leadership skills are required for this position."
    )
    data = {
        "job_description": sample_jd,
        "resume": (io.BytesIO(b"dummy resume content"), "resume.txt"),
    }
    response = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    res_data = response.get_json()
    assert res_data["code"] == "INVALID_EXTENSION"


def test_analyze_valid_sample_resume(client):
    sample_pdf_path = SAMPLES_DIR / "valid_sample_resume.pdf"
    if not sample_pdf_path.exists():
        pytest.skip("valid_sample_resume.pdf not found")

    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    sample_jd = (
        "We are looking for an experienced senior software engineer who has deep expertise "
        "in Python, Flask, FastAPI, PostgreSQL, and cloud deployments with Docker and Kubernetes. "
        "You will design scalable architectures, participate in code reviews, and drive engineering excellence. "
        "Strong communication, problem solving, and leadership skills are required for this position."
    )

    data = {
        "job_description": sample_jd,
        "resume": (io.BytesIO(pdf_bytes), "sample_resume.pdf"),
    }

    response = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert response.status_code == 200
    res_data = response.get_json()

    assert res_data["success"] is True
    assert "match" in res_data
    assert "overall_score" in res_data["match"]
    assert "profile" in res_data
    assert "ats_check" in res_data
    assert "ai_suggestions" in res_data
    assert "annotated_resume" in res_data

    # Check skills matching
    matched = res_data["match"]["skills"]["matched"]
    assert "Python" in matched
    assert "Flask" in matched
    assert "PostgreSQL" in matched


def test_analyze_scanned_image_pdf(client):
    scanned_pdf_path = SAMPLES_DIR / "scanned_image_resume.pdf"
    if not scanned_pdf_path.exists():
        pytest.skip("scanned_image_resume.pdf not found")

    with open(scanned_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    sample_jd = (
        "We are looking for an experienced senior software engineer who has deep expertise "
        "in Python, Flask, FastAPI, PostgreSQL, and cloud deployments with Docker and Kubernetes. "
        "You will design scalable architectures, participate in code reviews, and drive engineering excellence. "
        "Strong communication, problem solving, and leadership skills are required for this position."
    )

    data = {
        "job_description": sample_jd,
        "resume": (io.BytesIO(pdf_bytes), "scanned_resume.pdf"),
    }

    response = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert response.status_code == 422
    res_data = response.get_json()
    assert res_data["code"] == "SCANNED_OR_EMPTY_PDF"
