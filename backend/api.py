"""
api.py
The web API that the React frontend talks to.

Run it from the backend/ folder with:
    uvicorn api:app --reload
"""

import io

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from github_checker import RateLimitError, UserNotFoundError
from pipeline import run_check
from resume_parser import ResumeError, extract_text

app = FastAPI(title="ProofCheck API")

# Allow the React dev server (a different port = a different "origin")
# to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/check")
def check(
    resume: UploadFile = File(...),
    github_username: str = Form(...),
    required_skills: str = Form(""),
):
    # ---- 1. Check the inputs ----
    filename = resume.filename or ""
    if not filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Please upload a PDF or DOCX resume.")

    username = github_username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Please enter a GitHub username.")

    # "Python, React" -> ["Python", "React"]
    required = [s.strip() for s in required_skills.split(",") if s.strip()]

    # ---- 2. Run the pipeline, turning each error into a clear message ----
    try:
        file_bytes = io.BytesIO(resume.file.read())
        text = extract_text(file_bytes, filename)
        report = run_check(text, username, required)
    except ResumeError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except UserNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except RateLimitError as error:
        raise HTTPException(status_code=429, detail=str(error))
    except Exception as error:
        print(f"Unexpected error: {error!r}")  # shows in the backend terminal
        raise HTTPException(status_code=500, detail=f"Something went wrong: {error}")

    # ---- 3. Send everything back as JSON ----
    return report
