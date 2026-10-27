# AI Resume Analyzer

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1+-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4+-F7931E?style=flat&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-fitz-228B22?style=flat)](https://pymupdf.readthedocs.io/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-SDK-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/PyTest-29%20Passing-brightgreen?style=flat&logo=pytest&logoColor=white)](https://pytest.org)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=flat&logo=render&logoColor=white)](https://render.com)

**AI Resume Analyzer** is an intelligent, deployable resume analyzer and proofing engine. Built with an authentic **Neobrutalism** theme—featuring high-contrast borders, tactile offset shadows, and vibrant highlighter aesthetics—AI Resume Analyzer reviews candidate resumes with the scrutiny of a seasoned technical hiring manager.

---

## 1. Project Overview & Objectives

Traditional resume checkers are opaque "black boxes" that emit arbitrary percentages without actionable guidance. **AI Resume Analyzer** re-engineers resume analysis with full transparency, deep natural language parsing, and robust fallback safety:

- **Mathematical Rigor**: Blends n-gram TF-IDF cosine similarity with an extensive 340+ skill taxonomy.
- **ATS Compliance Auditing**: Evaluates structural parser compliance, contact validity, date consistency, and table/column fragmentation.
- **Action Phrasing Proofing**: Flags weak/passive verbs (`worked on`, `responsible for`, `helped`) and prompts for missing quantified metrics.
- **Deterministic Resiliency**: Powered by Google Gemini with strict JSON enforcement and an automatic local heuristic fallback engine that guarantees the app never crashes if external AI APIs fail or API keys are absent.

---

## 2. Neobrutalist UI Design

AI Resume Analyzer embraces a distinctive **Neobrutalism** design language:
- **Bold 3px High-Contrast Borders**: Sharp geometric boundaries across cards, inputs, and badges.
- **Hard Unblurred Drop Shadows**: `5px 5px 0px #000000` with tactile micro-interactions on hover and active states.
- **Vibrant Highlighter Accents**: Electric canary yellow (`#FFE600`), mint green (`#4ADE80`), coral red (`#FF5E5B`), and vivid cyan (`#38BDF8`).
- **Dark Neobrutalism Support**: Persistent dark mode toggling with high-contrast borders and neon accents.
- **Document-First Flow**: Numbered sections (`01` to `07`), an annotated manuscript view with inline highlights and floating margin notes.

---

## 3. Architecture & Data Flow

```
                      +------------------------------------------+
                      |         User Upload (PDF + Job Desc)     |
                      +------------------------------------------+
                                           |
                                           v
                       +----------------------------------------+
                       |        Flask Multipart Ingestion       |
                       | - Extension, MIME & %PDF- Magic Bytes  |
                       | - Size Validation (<= 5 MB)            |
                       +----------------------------------------+
                                           |
                                           v
                       +----------------------------------------+
                       |           PyMuPDF Text Extractor       |
                       | - Extracts selectable text & page maps |
                       | - Detects scanned / image-only PDFs    |
                       +----------------------------------------+
                                           |
                       +-------------------+--------------------+
                       |                                        |
                       v                                        v
        +----------------------------+           +----------------------------+
        |   Resume Entity Parser     |           |   Skills Taxonomy Engine   |
        | - Contact Info (Email/URL) |           | - 340+ Canonical Skills    |
        | - Education & GPA          |           | - 100+ Alias Normalization |
        | - Experience & Bullets     |           | - Category Overlap Map     |
        | - Technical Projects       |           +----------------------------+
        +----------------------------+                          |
                       |                                        |
                       +-------------------+--------------------+
                                           |
                                           v
                       +----------------------------------------+
                       |         Matching & Scoring Core        |
                       | - TF-IDF Vectorizer (Unigrams/Bigrams) |
                       | - Cosine Similarity Calculation        |
                       | - Blended Formula: 60% Skill + 40% Sim |
                       +----------------------------------------+
                                           |
                       +-------------------+--------------------+
                       |                                        |
                       v                                        v
        +----------------------------+           +----------------------------+
        |     ATS & Improver Core    |           |    Gemini AI Recommendation|
        | - 7-Point ATS Checklist    |           | - Google GenAI SDK Client  |
        | - Weak Action Verb Audit   |           | - Strict JSON Parse        |
        | - Unquantified Metrics Flag|           | - Heuristic Rule Fallback  |
        +----------------------------+           +----------------------------+
                                           |
                                           v
                       +----------------------------------------+
                       |      Neobrutalist Manuscript UI        |
                       | - Giant Typographic Verdict Score      |
                       | - Marked Up Skills & Category Bars     |
                       | - Single Chart.js Horizontal Bar Visual|
                       | - Annotated Document + Margin Notes    |
                       | - Markdown Export & Print Stylesheet   |
                       | - LocalStorage History Archive         |
                       +----------------------------------------+
```

---

## 4. How the Analysis Works

### A. The Scoring Formula
The final match score is a transparent composite defined in `services/matcher.py`:

$$\text{Final Score} = (0.60 \times \text{Skill Coverage Ratio}) + (0.40 \times \text{TF-IDF Cosine Similarity})$$

1. **Skill Coverage Ratio (60% weight)**:
   $$\text{Coverage} = \frac{|\text{Resume Skills} \cap \text{Job Description Skills}|}{|\text{Job Description Skills}|}$$
   - Matches both canonical skills and aliases (e.g. `js` $\rightarrow$ `JavaScript`, `k8s` $\rightarrow$ `Kubernetes`, `ml` $\rightarrow$ `Machine Learning`).
   - If the job description lists zero recognizable skills from the taxonomy, the engine smoothly transitions to 100% TF-IDF cosine similarity.

2. **TF-IDF Cosine Similarity (40% weight)**:
   - Uses `TfidfVectorizer` with sublinear term-frequency scaling (`sublinear_tf=True`), English stopword removal, and `ngram_range=(1, 2)`.
   - Captures shared technical phrases (e.g. `distributed systems`, `rest api`, `machine learning`, `ci cd`).
   - Normalizes vector dot products between candidate resume and job description to $[0.0, 1.0]$.

### B. Skill Taxonomy & Extraction (`data/skills.json`)
Curated dictionary containing **349 canonical skills** across 9 major industry domains:
1. Programming Languages (Python, Go, Rust, C++, TypeScript, SQL, etc.)
2. Frameworks & Libraries (React, Next.js, Flask, FastAPI, Django, Spring Boot, etc.)
3. Databases & Storage (PostgreSQL, MongoDB, Redis, Cassandra, Snowflake, etc.)
4. Cloud & DevOps (AWS, Docker, Kubernetes, Terraform, GitHub Actions, Linux, etc.)
5. Machine Learning & AI (PyTorch, TensorFlow, Hugging Face, LLMs, RAG, LangChain, etc.)
6. Data Engineering & Analytics (Apache Spark, Kafka, Airflow, dbt, etc.)
7. Developer Tools & Testing (Git, PyTest, Jest, Postman, Docker Compose, etc.)
8. Core Concepts & Architecture (Microservices, System Design, TDD, OOP, CI/CD, etc.)
9. Soft Skills & Professional (Problem Solving, Technical Writing, Leadership, etc.)

With **105+ alias mappings** and symbol-safe boundary regex logic preventing accidental substring collisions (e.g. prevents `.js` in `Next.js` from improperly tagging generic JavaScript).

### C. ATS & Improvement Auditing
- **ATS Readiness Index (0-100)**: Evaluates contact headers, email validity, telephone format, online profile presence (LinkedIn / GitHub), length suitability (400-1100 words), date chronology consistency, and column/table fragmentation.
- **Weak Action Verb Detection**: Scans bullets for passive verbs (`worked on`, `assisted with`, `responsible for`) and provides power verb alternatives (`Spearheaded`, `Architected`, `Delivered`).
- **Missing Metrics Flag**: Flags accomplishments lacking quantifiable outcomes (`%`, `throughput`, `latency`, `user scale`).

### D. AI Suggestions & Resilient Fallback (`services/ai_client.py`)
- Calls Google Gemini using the official `google-genai` SDK (`gemini-2.5-flash`).
- Prompts for strict JSON containing:
  - Executive summary from a technical hiring editor.
  - 5 to 7 concrete improvements.
  - 3 to 5 rewritten bullet points using the $[ \text{Action Verb} + \text{Task} + \text{Tech Tool} + \text{Quantified Metric} ]$ formula.
  - A tailored professional summary.
- **Resilient Fallback**: If `GEMINI_API_KEY` is omitted, or if the API times out/fails, AI Resume Analyzer activates its internal deterministic editorial engine. The candidate receives high-utility rule-based suggestions and a polite status badge. **The application never crashes.**

---

## 5. Repository Structure

```
AI resume analyser/
├── app.py                      # Flask application factory, error handlers, and API routes
├── services/
│   ├── __init__.py             # Services package marker
│   ├── pdf_extractor.py        # PyMuPDF ingestion, magic byte verification, scanned PDF check
│   ├── parser.py               # Resume section, education, experience, project parser
│   ├── skills.py               # Skills taxonomy loading, alias lookup, overlap engine
│   ├── matcher.py              # TF-IDF cosine similarity, weighted formula, verdict generator
│   ├── ats.py                  # ATS readiness scoring and compliance checklist
│   ├── improver.py             # Weak action verbs, missing metrics, and bullet audit
│   └── ai_client.py            # Gemini SDK client with strict JSON and heuristic fallback
├── data/
│   └── skills.json             # 349 canonical skills across 9 categories + 105 aliases
├── templates/
│   └── index.html              # Neobrutalist single-page application template
├── static/
│   ├── css/
│   │   └── style.css           # Neobrutalism design system, dark mode, print styles
│   └── js/
│       ├── app.js              # Frontend controller, form handling, Chart.js visual
│       ├── history.js          # LocalStorage analysis archive manager
│       └── report.js           # Markdown export generator and print triggering
├── samples/
│   ├── sample_job_description.txt # Realistic Senior Backend Engineer job description
│   ├── create_sample_resumes.py   # Automated generator for test PDF resumes
│   ├── valid_sample_resume.pdf    # Clean valid test resume
│   ├── scanned_image_resume.pdf   # Scanned image test PDF (no text)
│   └── corrupted_resume.pdf       # Malformed test PDF
├── tests/
│   ├── __init__.py
│   ├── test_pdf_extractor.py   # PDF upload validation, size limit, and extraction tests
│   ├── test_parser.py          # Entity parsing, contacts, and section tests
│   ├── test_skills.py          # Taxonomy, alias resolution, and overlap tests
│   ├── test_matcher.py         # TF-IDF, formula weights, and verdict tests
│   ├── test_ats_improver.py    # ATS scoring, weak verbs, and metrics tests
│   └── test_api.py             # Flask route integration and error handler tests
├── Procfile                    # web: gunicorn app:app
├── render.yaml                 # Infrastructure-as-code blueprint for Render
├── runtime.txt                 # python-3.11.9
├── requirements.txt            # Production dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules (.env, venv, uploads, *.pdf)
└── README.md                   # Comprehensive documentation
```

---

## 6. Environment Variables

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `GEMINI_API_KEY` | Optional | `""` | Google Gemini API key. If omitted, local heuristic engine is used. |
| `GEMINI_MODEL` | Optional | `gemini-2.5-flash` | Gemini model identifier used for analysis. |
| `MAX_CONTENT_LENGTH` | Optional | `5242880` | Maximum file upload size in bytes (5 MB). |
| `SECRET_KEY` | Optional | `dev-secret-key` | Flask session and CSRF signing secret. |
| `PORT` | Optional | `5000` | Port for the local or production web server. |
| `FLASK_ENV` | Optional | `production` | Flask runtime environment (`development` / `production`). |

---

## 7. Local Setup & Installation

### Prerequisites
- Python 3.11 or higher
- Git

### Step-by-Step Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/raktikghosh/ai-resume-analyzer.git
   cd ai-resume-analyzer
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env and paste your GEMINI_API_KEY (optional)
   ```

5. **Generate Test Sample Resumes**:
   ```bash
   python samples/create_sample_resumes.py
   ```

6. **Run the Development Server**:
   ```bash
   python app.py
   ```
   Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 8. Running the Automated Test Suite

The test suite contains **29 comprehensive unit and integration tests** covering extraction, parsing, vectorization, ATS compliance, and API routes.

```bash
# Run all tests with verbose output
pytest -v

# Run with test coverage report
pytest --cov=services --cov=app tests/
```

Test coverage summary:
- `tests/test_skills.py`: Taxonomy loading, alias mapping, boundary regex, overlap math.
- `tests/test_pdf_extractor.py`: Real PDF magic bytes, MIME types, 5 MB limits, scanned PDF detection.
- `tests/test_parser.py`: Contacts, education GPA parsing, experience dates, project extraction.
- `tests/test_matcher.py`: TF-IDF vectorization, 60/40 weighted formula, verdict grading.
- `tests/test_ats_improver.py`: ATS checklist scoring, weak verbs, unquantified metrics.
- `tests/test_api.py`: Route status codes (200, 400, 413, 422), multipart file uploads, rate limiting.

---

## 9. API Reference

### `GET /api/health`
Returns system status, environment, and AI configuration state.

**Response `(200 OK)`**:
```json
{
  "status": "healthy",
  "app": "AI Resume Analyzer",
  "version": "1.0.0",
  "environment": "development",
  "ai_configured": true,
  "ai_model": "gemini-2.5-flash",
  "timestamp": "2026-10-25T02:30:00.000Z"
}
```

### `POST /api/analyze`
Submits a PDF resume and job description for comprehensive analysis.
- **Content-Type**: `multipart/form-data`
- **Rate Limit**: 20 requests per minute

**Parameters**:
- `resume` (file, required): `.pdf` document ($\le 5\text{ MB}$, valid `%PDF-` signature).
- `job_description` (text, required): Target job description ($\ge 40\text{ words}$).

**Success Response `(200 OK)`**:
```json
{
  "success": true,
  "timestamp": "2026-10-25T02:30:00.000Z",
  "metadata": {
    "filename": "valid_sample_resume.pdf",
    "file_size": 2848,
    "page_count": 1,
    "word_count": 285,
    "jd_word_count": 128
  },
  "match": {
    "overall_score": 78,
    "verdict": "Strong alignment. Core technical competencies are well represented...",
    "scoring_breakdown": {
      "formula": "Final = (60% * Skill Coverage) + (40% * TF-IDF Cosine Similarity)",
      "weights": { "skills_weight": 0.6, "cosine_weight": 0.4 },
      "skill_coverage_score": 77.8,
      "tfidf_cosine_score": 78.4
    },
    "skills": {
      "matched": ["Docker", "FastAPI", "Flask", "Kubernetes", "PostgreSQL", "Python", "Redis"],
      "missing": ["Apache Kafka", "Prometheus"],
      "extra": ["Go", "GraphQL", "MongoDB", "TypeScript"],
      "matched_count": 7,
      "missing_count": 2,
      "coverage_by_category": { ... }
    }
  },
  "profile": {
    "contacts": { "email": "alex.chen.dev@example.com", "phone": "(555) 234-5678", ... },
    "education": [ ... ],
    "experience": [ ... ],
    "projects": [ ... ],
    "certifications": [ ... ]
  },
  "ats_check": {
    "score": 85,
    "checklist": [ ... ],
    "passed_count": 6,
    "warning_count": 1,
    "fail_count": 0,
    "summary": "ATS readiness score: 85/100. 6 checks passed, 1 warnings, 0 critical fixes required."
  },
  "improvement_assistant": {
    "weak_verbs_detected": [ ... ],
    "bullets_missing_metrics": [ ... ],
    "metric_coverage_percentage": 75.0
  },
  "ai_suggestions": {
    "executive_summary": "...",
    "actionable_suggestions": [ ... ],
    "rewritten_bullets": [ ... ],
    "tailored_professional_summary": "...",
    "ai_powered": true
  },
  "annotated_resume": {
    "raw_text": "...",
    "annotations": [ ... ],
    "margin_notes": [ ... ]
  }
}
```

**Error Responses**:
- `400 Bad Request`: `{"error": "Job description is too brief (12 words provided)...", "code": "JD_TOO_SHORT"}`
- `400 Bad Request`: `{"error": "Invalid file extension for 'photo.png'...", "code": "INVALID_EXTENSION"}`
- `413 Payload Too Large`: `{"error": "The uploaded PDF exceeds the 5 MB maximum...", "code": "FILE_TOO_LARGE"}`
- `422 Unprocessable Entity`: `{"error": "This PDF appears to be a scanned image...", "code": "SCANNED_OR_EMPTY_PDF"}`
- `429 Too Many Requests`: `{"error": "Rate limit exceeded...", "code": "RATE_LIMIT_EXCEEDED"}`

---

## 10. Production Deployment on Render

AI Resume Analyzer includes out-of-the-box configuration for instant deployment on [Render](https://render.com).

### Method 1: Deploy with `render.yaml` Blueprint (Recommended)
1. Fork or push this repository to your GitHub account.
2. Log in to the [Render Dashboard](https://dashboard.render.com).
3. Click **New** $\rightarrow$ **Blueprint**.
4. Connect your repository. Render automatically reads `render.yaml`:
   - **Environment**: Python 3.11.9
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Enter your `GEMINI_API_KEY` under the Environment Variables prompt.
6. Click **Apply**.

### Method 2: Manual Web Service Setup
1. Click **New Web Service** on Render.
2. Set **Build Command**: `pip install -r requirements.txt`
3. Set **Start Command**: `gunicorn app:app`
4. Set Environment Variables:
   - `PYTHON_VERSION`: `3.11.9`
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `GEMINI_API_KEY`: `<your_gemini_api_key>`
   - `SECRET_KEY`: `<generate_random_secret>`
   - `MAX_CONTENT_LENGTH`: `5242880`

---

## 11. Security, Privacy & Integrity

1. **Zero Resume Persistence**: Candidate resumes and PDF files are processed purely in-memory as byte streams. No resume files are ever written to disk or stored in databases.
2. **Privacy-Preserving Logs**: Sensitive PII (names, emails, phones, resume contents) are never emitted into application logs. Only high-level metric counts and scores are logged.
3. **Client-Side History Privacy**: Analysis history is saved strictly in the user's browser `localStorage`. Results can be inspected or deleted at any time.
4. **Environment Isolation**: API credentials are read strictly from environment variables (`.env` locally, Render Secrets in production). The `.env` file is excluded in `.gitignore`.

---

## 12. Limitations & Future Roadmap

### Current Limitations
- **OCR Scanning**: While scanned PDFs are detected and guided with helpful instructions, OCR (Optical Character Recognition) is not executed server-side to prevent high latency and server memory exhaustion.
- **Language Scope**: Currently optimized for English-language technical and professional resumes.

### Future Roadmap
- **Client-Side WASM OCR**: Optional client-side Tesseract.js fallback for scanned resumes before upload.
- **Multi-Role Comparison**: Compare a single resume simultaneously against multiple job openings to identify best-fit positions.
- **Custom Taxonomy Uploads**: Allow recruiters or university placement cells to provide bespoke skill taxonomies.

---

## 13. License & Acknowledgements

Developed with ❤️.
Licensed under the [MIT License](LICENSE).
