"""Script to generate realistic sample PDF resumes for testing and demonstrations.

Creates:
1. samples/valid_sample_resume.pdf - Clean, valid software engineering resume
2. samples/scanned_image_resume.pdf - PDF with an image/drawing and zero selectable text
3. samples/corrupted_resume.pdf - Malformed PDF file for error resilience tests
"""

from pathlib import Path
import fitz  # PyMuPDF

SAMPLES_DIR = Path(__file__).resolve().parent
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def create_valid_resume():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)  # Standard US Letter size

    resume_text = """ALEX CHEN
alex.chen.dev@example.com | (555) 234-5678 | San Francisco, CA
linkedin.com/in/alexchen-dev | github.com/alexchen-dev

PROFESSIONAL SUMMARY
Results-driven Senior Software Engineer with 4+ years of hands-on experience designing and delivering scalable backend services, distributed systems, and data pipelines. Proven track record in Python, PostgreSQL, and cloud deployments.

TECHNICAL SKILLS
- Programming Languages: Python, JavaScript, TypeScript, Go, SQL, Bash
- Frameworks & Libraries: Flask, FastAPI, Django, React, Node.js, REST APIs, GraphQL
- Databases & Storage: PostgreSQL, Redis, MongoDB, SQLite
- Cloud & DevOps: Docker, Kubernetes, AWS, CI/CD, GitHub Actions, Linux, Nginx
- Developer Tools & Methodologies: Git, PyTest, Agile, Scrum, Test-Driven Development, System Design

PROFESSIONAL EXPERIENCE
Senior Backend Engineer | Apex Cloud Solutions | July 2022 - Present
- Architected and deployed microservices in Python and Flask handling 12M+ monthly API requests.
- Optimized PostgreSQL queries and caching strategies with Redis, decreasing average p99 latency by 42%.
- Championed automated CI/CD workflows using GitHub Actions and Docker, reducing release cycles from 3 days to 45 minutes.
- Spearheaded code reviews and mentored 4 junior engineers in Test-Driven Development practices.

Software Engineer | NextGen Digital | August 2020 - June 2022
- Engineered high-throughput REST APIs and web scrapers using Python, FastAPI, and BeautifulSoup.
- Responsible for database normalization and maintenance across production PostgreSQL clusters.
- Collaborated with frontend engineers to integrate React applications with backend microservices.
- Implemented unit and integration test suites using PyTest, achieving 91% code coverage.

KEY PROJECTS
AI Resume Analyzer | Python, Flask, PyMuPDF, Scikit-Learn | github.com/alexchen-dev/ai-resume-analyzer
- Built an intelligent resume proofing web application that parses PDF resumes and calculates TF-IDF match scores.
- Implemented ATS validation checklists, weak action verb auditing, and LLM-assisted bullet point revisions.

Distributed Task Queue | Go, Redis, Docker | github.com/alexchen-dev/task-queue
- Designed an asynchronous distributed task processor in Go supporting retry policies and priority scheduling.

EDUCATION
B.Tech in Computer Science and Engineering
Institute of Engineering & Management, Kolkata | 2016 - 2020 | CGPA: 8.7 / 10.0

CERTIFICATIONS
- AWS Certified Solutions Architect - Associate | Amazon Web Services (2023)
- HashiCorp Certified: Terraform Associate (2022)
"""

    # Insert text into page
    rect = fitz.Rect(40, 40, 572, 752)
    page.insert_textbox(rect, resume_text, fontsize=9.5, fontname="helv", align=0)

    output_path = SAMPLES_DIR / "valid_sample_resume.pdf"
    doc.save(output_path)
    doc.close()
    print(f"Created valid sample resume: {output_path} ({output_path.stat().st_size} bytes)")


def create_scanned_image_resume():
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Draw geometric shapes to mimic a scanned image without real text characters
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(50, 50, 562, 742))
    shape.finish(color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95), width=2)

    # Add a mock photo box
    shape.draw_rect(fitz.Rect(70, 70, 150, 150))
    shape.finish(color=(0.5, 0.5, 0.5), fill=(0.7, 0.7, 0.7), width=1)
    shape.commit()

    # Insert just 3 characters so word_count < 10 and char_count < 50
    page.insert_text(fitz.Point(70, 170), "IMG", fontsize=8)

    output_path = SAMPLES_DIR / "scanned_image_resume.pdf"
    doc.save(output_path)
    doc.close()
    print(f"Created scanned image PDF: {output_path} ({output_path.stat().st_size} bytes)")


def create_corrupted_resume():
    output_path = SAMPLES_DIR / "corrupted_resume.pdf"
    # Write invalid non-PDF binary data with a .pdf extension
    with open(output_path, "wb") as f:
        f.write(b"CORRUPTED_NOT_A_REAL_PDF_DATA\x00\xFF\xFE\xFD" * 20)
    print(f"Created corrupted PDF: {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    create_valid_resume()
    create_scanned_image_resume()
    create_corrupted_resume()
