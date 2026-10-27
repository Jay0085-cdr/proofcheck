"""
claims.py
Turns resume text into the skills and projects the candidate claims.

Two modes:
  - "ai":    Claude reads the resume (needs an API key with credits)
  - "basic": free, no AI. Simple text rules find keywords and projects.
If the AI can't be used for any reason, we fall back to basic mode.
"""

import json
import os
import re

import anthropic
from dotenv import load_dotenv

# Load ANTHROPIC_API_KEY from the .env file
load_dotenv()

MODEL = "claude-haiku-5-5"

PROMPT = """You are helping a recruiter read a resume.
Extract the candidate's skills and projects from the resume below.

Return ONLY valid JSON, with no extra text, in exactly this format:
{
  "skills": ["Python", "React"],
  "projects": [
    {
      "name": "Chat App",
      "tech": ["Node.js", "Redis"],
      "claims": ["handles 5000 users"]
    }
  ]
}

Rules:
- "skills": every technical skill, language, framework or tool mentioned.
- "projects": each project the candidate built.
  - "tech": technologies used in that project.
  - "claims": specific achievements or numbers they state about it.
- Only include what is actually written in the resume. Do not guess.
- If something is missing, use an empty list [].

Resume:
\"\"\"
{resume_text}
\"\"\"
"""


# ---------------------------------------------------------------
# AI helpers (also used by questions.py)
# ---------------------------------------------------------------

def has_api_key():
    """True if a real-looking Anthropic key is set."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return key.startswith("sk-")


def strip_code_fences(text):
    """Remove ```json ... ``` fences if Claude added them."""
    text = text.strip()
    if text.startswith("```"):
        # Drop the first line (``` or ```json)
        text = text.split("\n", 1)[1] if "\n" in text else ""
        # Drop the closing ```
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def ask_claude(prompt):
    """Send a prompt to Claude and return its reply as plain text."""
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY automatically

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    # The reply can contain several blocks; we only want the text ones
    reply = ""
    for block in response.content:
        if block.type == "text":
            reply += block.text
    return reply


def extract_claims_ai(resume_text):
    """AI version. Tries twice; raises ValueError if the JSON is still bad."""
    prompt = PROMPT.replace("{resume_text}", resume_text)
    last_reply = ""

    for attempt in range(2):  # first try + one retry
        last_reply = ask_claude(prompt)
        try:
            data = json.loads(strip_code_fences(last_reply))
        except json.JSONDecodeError:
            print(f"Attempt {attempt + 1}: reply was not valid JSON, retrying...")
            continue

        # Make sure both keys always exist so later code doesn't crash
        data.setdefault("skills", [])
        data.setdefault("projects", [])
        return data

    raise ValueError(f"Could not get valid JSON from Claude. Last reply:\n{last_reply}")


# ---------------------------------------------------------------
# Basic (no-AI) mode
# ---------------------------------------------------------------

# Display name -> spellings to search for (all lowercase)
TECH_KEYWORDS = {
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript"],
    "TypeScript": ["typescript"], "C++": ["c++"], "C#": ["c#"],
    "Go": ["golang"], "Kotlin": ["kotlin"], "PHP": ["php"], "Ruby": ["ruby"],
    "Rust": ["rust"], "HTML": ["html"], "CSS": ["css"], "SQL": ["sql"],
    "React": ["react", "react.js", "reactjs"], "Next.js": ["next.js", "nextjs"],
    "Angular": ["angular"], "Vue": ["vue", "vue.js"],
    "Node.js": ["node.js", "nodejs"], "Express": ["express", "express.js"],
    "Django": ["django"], "Flask": ["flask"], "FastAPI": ["fastapi"],
    "Spring Boot": ["spring boot", "springboot"], "Hibernate": ["hibernate"],
    "Tailwind CSS": ["tailwind"], "Bootstrap": ["bootstrap"],
    "GraphQL": ["graphql"], "REST API": ["rest api", "restful"],
    "MySQL": ["mysql"], "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb"], "Redis": ["redis"], "SQLite": ["sqlite"],
    "Firebase": ["firebase"], "Docker": ["docker"], "Kubernetes": ["kubernetes"],
    "AWS": ["aws"], "Azure": ["azure"], "GCP": ["gcp", "google cloud"],
    "Git": ["git"], "GitHub": ["github"], "Linux": ["linux"],
    "Postman": ["postman"], "Jenkins": ["jenkins"], "JWT": ["jwt"],
    "Flyway": ["flyway"], "TensorFlow": ["tensorflow"], "PyTorch": ["pytorch"],
    "Pandas": ["pandas"], "NumPy": ["numpy"], "Scikit-learn": ["scikit-learn", "sklearn"],
}

# Words that appear in resume section headings
SECTION_WORDS = ["education", "experience", "projects", "skills", "certifications",
                 "achievements", "awards", "summary", "objective", "internships",
                 "publications", "activities", "interests", "languages", "leadership"]

BULLETS = ("•", "-", "*", "◦", "▪", "●", "–")


def find_keywords(text):
    """Return the tech keywords that appear in `text` as whole words.
    So "Java" does NOT match inside "JavaScript"."""
    text = text.lower()
    found = []
    for name, spellings in TECH_KEYWORDS.items():
        for word in spellings:
            pattern = r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9+#])"
            if re.search(pattern, text):
                found.append(name)
                break
    return found


def is_section_heading(line):
    """A short line like "PROJECTS" or "Technical Skills"."""
    clean = line.strip().rstrip(":").strip()
    if not clean or len(clean.split()) > 4 or clean.startswith(BULLETS):
        return False
    has_section_word = any(word in clean.lower() for word in SECTION_WORDS)
    # All caps ("TECHNICAL SKILLS") or exactly a heading ("Projects")
    return has_section_word and (clean.isupper() or clean.lower() in SECTION_WORDS)


def is_project_title(line):
    """A project title: not a bullet, starts with a capital letter,
    is fairly short and doesn't end like a sentence."""
    line = line.strip()
    return (
        line != ""
        and not line.startswith(BULLETS)
        and line[0].isupper()
        and not line.endswith(".")
        and len(line.split()) <= 12
    )


def clean_project_name(line):
    """'Chat App | React | Jan 2024' -> 'Chat App'."""
    name = re.split(r"\t| \| |\|", line)[0]
    # Remove a date at the end, like "January 2026" or "2023 - Present"
    name = re.sub(r"\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}.*$",
                  "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+\d{4}\s*([-–]\s*(\d{4}|present|current))?\s*$", "", name, flags=re.IGNORECASE)
    return name.strip()


def find_projects(text):
    """Find the Projects section and split it into projects."""
    projects = []
    current = None
    in_projects = False

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Section headings switch us in or out of the Projects section
        if is_section_heading(line):
            in_projects = "project" in line.lower()
            continue
        if not in_projects:
            continue

        if is_project_title(line):
            # A new project starts
            current = {"name": clean_project_name(line), "title": line, "bullets": []}
            projects.append(current)
        elif current and line.startswith(BULLETS):
            # A new bullet point (remove the bullet character)
            current["bullets"].append(line.lstrip("".join(BULLETS) + " "))
        elif current and current["bullets"]:
            # A long bullet that wrapped onto the next line: join it back
            current["bullets"][-1] += " " + line
        elif current:
            current["bullets"].append(line)

    # Turn each project into name + tech + claims
    results = []
    for p in projects:
        all_text = p["title"] + " " + " ".join(p["bullets"])
        # Claims = bullet points that mention a number (e.g. "5000 users")
        claims = [b for b in p["bullets"] if re.search(r"\d", b)]
        results.append({"name": p["name"], "tech": find_keywords(all_text), "claims": claims})
    return results


def extract_claims_basic(resume_text):
    return {
        "skills": find_keywords(resume_text),
        "projects": find_projects(resume_text),
    }


# ---------------------------------------------------------------
# Main function: try AI, fall back to basic
# ---------------------------------------------------------------

def extract_claims(resume_text):
    """
    Returns {"mode": "ai" or "basic", "skills": [...], "projects": [...]}.
    Uses Claude if possible; otherwise uses the free basic rules.
    """
    if has_api_key():
        try:
            data = extract_claims_ai(resume_text)
            data["mode"] = "ai"
            return data
        except (anthropic.APIError, ValueError) as error:
            # Covers no credits, bad key, network problems and bad JSON
            print(f"AI extraction failed, using basic mode instead: {error}")

    data = extract_claims_basic(resume_text)
    data["mode"] = "basic"
    return data
