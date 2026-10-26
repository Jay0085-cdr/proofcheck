"""
claims.py
Sends resume text to Claude and gets back the skills and projects
the candidate claims, as a Python dictionary.
"""

import json

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


def ask_claude(resume_text):
    """Send the prompt to Claude and return its reply as plain text."""
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY automatically

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[
            {"role": "user", "content": PROMPT.replace("{resume_text}", resume_text)}
        ],
    )

    # The reply can contain several blocks; we only want the text ones
    reply = ""
    for block in response.content:
        if block.type == "text":
            reply += block.text
    return reply


def extract_claims(resume_text):
    """
    Turn resume text into a dict like:
    {"skills": [...], "projects": [{"name": ..., "tech": [...], "claims": [...]}]}

    Tries twice. If Claude's reply still isn't valid JSON, raises an error.
    """
    last_reply = ""

    for attempt in range(2):  # first try + one retry
        last_reply = ask_claude(resume_text)
        try:
            data = json.loads(strip_code_fences(last_reply))
        except json.JSONDecodeError:
            print(f"Attempt {attempt + 1}: reply was not valid JSON, retrying...")
            continue

        # Make sure both keys always exist so later code doesn't crash
        data.setdefault("skills", [])
        data.setdefault("projects", [])
        return data

    raise ValueError(
        "Could not get valid JSON from Claude after 2 attempts.\n"
        f"Last reply was:\n{last_reply}"
    )
