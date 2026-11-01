# ProofCheck

ProofCheck checks the claims in a resume against the candidate's public GitHub
work and suggests interview questions for anything it can't confirm.

**It never rejects anyone.** It only shows the evidence it found, so the
interviewer knows what to ask about.

## What it does

1. **Reads the resume** (PDF or DOCX) and turns it into plain text.
2. **Extracts claims**: the skills and projects listed, plus the tech each project used.
   - **AI mode** uses Claude (`claude-haiku-5-5`) when an API key with credits is set.
   - **Basic mode (no AI)** is free. It uses simple text rules and runs automatically
     when there's no key or the API call fails.
3. **Checks GitHub**: fetches the user's public repos, their languages and
   dependency files, and who made the commits and when.
4. **Matches projects to repos** and gives each project a status:
   - 🟢 **Verified**: a matching repo exists, every claimed technology was found, and nothing looks suspicious
   - 🟠 **Partial**: a repo matches, but some tech is missing or there are red flags
   - ⚪ **No evidence**: no matching repo
5. **Job fit**: the percentage of the recruiter's required skills that appear in the resume.
6. **Interview questions** for Partial and No evidence projects.

### Red flags

- The repo is a fork
- The candidate made no commits, or fewer than 5
- All of the candidate's commits were made on one day
- Most commits were made by other accounts

## Project structure

```
proofchecK/
├── backend/                 Python + FastAPI
│   ├── api.py               Web API (POST /api/check, GET /api/health)
│   ├── resume_parser.py     PDF / DOCX → text
│   ├── claims.py            Text → skills + projects (AI or basic mode)
│   ├── github_checker.py    Fetches repo evidence from the GitHub API
│   ├── matcher.py           Project ↔ repo matching, statuses, red flags, job fit
│   ├── questions.py         Interview questions (AI or templates)
│   ├── test_day2.py         Manual test: resume → claims
│   ├── test_day3.py         Manual test: GitHub checker
│   ├── test_day4.py         Manual test: full pipeline report
│   └── requirements.txt
├── frontend/                React (Vite) + plain CSS
│   ├── src/App.jsx          The single page: form + report
│   ├── src/App.css
│   └── .env.example         VITE_API_URL=http://localhost:8000
└── .env.example             ANTHROPIC_API_KEY, GITHUB_TOKEN (both optional)
```

## Setup (one time)

You need Python 3.10+ and Node.js 18+.

```bash
# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env          # optional: add ANTHROPIC_API_KEY / GITHUB_TOKEN

# Frontend
cd frontend
npm install
cp .env.example .env          # sets VITE_API_URL=http://localhost:8000
```

Both keys are optional:
- Without `ANTHROPIC_API_KEY`, ProofCheck runs in **basic mode**.
- Without `GITHUB_TOKEN`, GitHub allows only 60 requests an hour. Add a token if you hit the rate limit.

## Running the app

You need two terminals.

**Terminal 1: backend**

```bash
cd proofchecK
source venv/bin/activate
cd backend
uvicorn api:app --reload
```

The backend runs at http://localhost:8000. Check that it's up at http://localhost:8000/api/health.

**Terminal 2: frontend**

```bash
cd proofchecK/frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

## API

### `GET /api/health`

```json
{"status": "ok"}
```

### `POST /api/check`

Multipart form data:

| Field             | Example                         |
|-------------------|---------------------------------|
| `resume`          | a `.pdf` or `.docx` file        |
| `github_username` | `octocat`                       |
| `required_skills` | `Python, React, SQL` (optional) |

```bash
curl -X POST http://localhost:8000/api/check \
  -F "resume=@resume.docx" \
  -F "github_username=octocat" \
  -F "required_skills=Python, React, SQL"
```

The response is JSON with `mode`, `skills`, `job_fit` (`score`, `matched`, `missing`),
`projects` (each with `status`, `repo`, `tech`, `flags`) and `questions`.

Errors come back as `{"detail": "..."}` with these status codes:

| Code | Meaning                                       |
|------|-----------------------------------------------|
| 400  | Not a PDF or DOCX, or the file has no text     |
| 404  | GitHub user not found                          |
| 429  | GitHub rate limit reached                      |
| 500  | Any other error                                |

## Manual tests

Run these from `backend/` with the venv active:

```bash
python test_day2.py resume.docx                          # resume → claims
python test_day3.py octocat                              # GitHub evidence
python test_day4.py resume.docx octocat "Python, React"  # full report
```

To force basic mode while testing: `ANTHROPIC_API_KEY= python test_day4.py ...`

## Progress

- **Day 1–2**: Project setup, PDF parser, claim extraction with Claude
- **Day 3**: GitHub evidence checker (languages, dependencies, commits, authors)
- **Day 4**: Matcher (project ↔ repo, statuses, red flags, job fit)
- **Day 5**: FastAPI backend, React frontend, DOCX support, free no-AI basic mode, interview questions

## Limitations

- Basic mode only knows a fixed list of tech keywords (in `claims.py`), so it misses
  anything not on the list and typos such as "MongoD".
- Only **public** repos are checked. Private or company work shows as "No evidence".
  That's why ProofCheck suggests questions and never rejects.
- Project ↔ repo matching uses name similarity, so a repo with a very different name may not match.
