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
   dependency files (`package.json`, `requirements.txt`, `pom.xml`, `build.gradle`),
   and who made the commits and when. The username box also accepts a full
   GitHub link such as `https://github.com/octocat`.
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
- The repo is mostly a copy of another public repo (see below)

### Copied project detector

Git gives every file a **blob SHA**, a fingerprint of its exact contents.
Identical files have identical SHAs, even in different repos. For each matched
repo, ProofCheck:

1. Picks up to 5 possible sources: the fork parent (if it's a fork) plus GitHub
   search results for the repo name and the project's name and tech, most stars first,
   excluding the candidate's own repos.
2. Downloads the file lists (Git Trees API, one call per repo, no file contents)
   and counts how many of the candidate's **source files** have the same SHA.
3. Adds a red flag if at least 50% of the source files, and at least 5 files, are identical:
   *"39 of 39 source files are identical to owner/repo (5611 stars)"*.

Boilerplate never counts: licence, README, `.gitignore`, lock files, files in
`node_modules`/`dist`/`build`, empty files, and starter files from Vite or Create React App.
The list is `IGNORED_FILES` in `backend/copy_detector.py`. File lists are cached
for each check, searches are capped, and if search fails the check is skipped.

### Two views

- **Recruiter** (default): interview questions for weak projects.
- **Check myself**: a fix-it list for candidates, for example:
  - commits made with an email that isn't linked to your GitHub account
  - projects with no public repo
  - claimed tech that isn't in the repo
  - forked or copied repos
  - likely tech typos on the resume ("MongoD" → "MongoDB")

### Commit timeline

Each project card shows a small bar chart of the candidate's commits per week,
with a label such as *"Built over 6 weeks"* or *"All commits on 1 day"*.

## Project structure

```
proofchecK/
├── backend/                 Python + FastAPI
│   ├── api.py               Web API (POST /api/check, GET /api/health)
│   ├── resume_parser.py     PDF / DOCX → text
│   ├── claims.py            Text → skills + projects (AI or basic mode)
│   ├── pipeline.py          Runs every step in order (used by api.py and test_day4.py)
│   ├── github_checker.py    Fetches repo evidence from the GitHub API
│   ├── copy_detector.py     Finds repos copied from popular public repos (blob SHAs)
│   ├── matcher.py           Project ↔ repo matching, statuses, red flags, job fit
│   ├── timeline.py          Commits per week for the bar chart
│   ├── questions.py         Interview questions (AI or templates)
│   ├── fixes.py             "Check myself" fix-it list and typo finder
│   ├── test_day2.py         Manual test: resume → claims
│   ├── test_day3.py         Manual test: GitHub checker
│   ├── test_day4.py         Manual test: full pipeline report
│   ├── test_copy.py         Tests: copy detector (one copied repo, one original)
│   ├── test_self_check.py   Tests: fix-it list and typos
│   ├── test_timeline.py     Tests: commits per week
│   ├── test_username.py     Tests: GitHub link → username
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
| `github_username` | `octocat` or `https://github.com/octocat` |
| `required_skills` | `Python, React, SQL` (optional) |
| `view`            | `recruiter` (default) or `self` |

```bash
curl -X POST http://localhost:8000/api/check \
  -F "resume=@resume.docx" \
  -F "github_username=octocat" \
  -F "required_skills=Python, React, SQL"
```

The response is JSON with `mode`, `view`, `skills`, `job_fit` (`score`, `matched`, `missing`)
and `projects` (each with `status`, `repo`, `tech`, `flags`, `copy`, `timeline` and
`timeline_label`). It also has `questions` in recruiter view, or `fixes` in self view.

Errors come back as `{"detail": "..."}` with these status codes:

| Code | Meaning                                       |
|------|-----------------------------------------------|
| 400  | Not a PDF or DOCX, no text, or a bad `view`    |
| 404  | GitHub user not found                          |
| 429  | GitHub rate limit reached                      |
| 500  | Any other error                                |

## Manual tests

Run these from `backend/` with the venv active:

```bash
python test_day2.py resume.docx                          # resume → claims
python test_day3.py octocat                              # GitHub evidence
python test_day4.py resume.docx octocat "Python, React"  # full report
python test_day4.py resume.docx octocat "Python, React" self  # fix-it list

python test_username.py     # no internet needed
python test_self_check.py   # no internet needed
python test_timeline.py
python test_copy.py
```

To force basic mode while testing: `ANTHROPIC_API_KEY= python test_day4.py ...`

## Progress

- **Day 1–2**: Project setup, PDF parser, claim extraction with Claude
- **Day 3**: GitHub evidence checker (languages, dependencies, commits, authors)
- **Day 4**: Matcher (project ↔ repo, statuses, red flags, job fit)
- **Day 5**: FastAPI backend, React frontend, DOCX support, free no-AI basic mode, interview questions
- **Day 6**: Copied project detector, "Check myself" mode, commit timeline, GitHub links
  in the username box, Maven/Gradle dependency files

## Limitations

- Basic mode only knows a fixed list of tech keywords (in `claims.py`), so it misses
  anything not on the list and typos such as "MongoD".
- Only **public** repos are checked. Private or company work shows as "No evidence".
  That's why ProofCheck suggests questions and never rejects.
- Project ↔ repo matching uses name similarity, so a repo with a very different name may not match.
- Only the latest 100 commits per repo are read, so the timeline and red flags only cover those commits.
- Commits only count as the candidate's if the commit email is linked to their GitHub account.
- The copy detector only finds byte-for-byte identical files. A copy with renamed
  variables or reformatted code won't match.
- The typo finder only catches near-misses of names in the keyword list.
