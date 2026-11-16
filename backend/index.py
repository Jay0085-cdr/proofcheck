"""
index.py
Entry point for Vercel. Vercel looks for a FastAPI "app" in a file named
index.py (or app.py / main.py), so we just re-export the one from api.py.
Locally you still run: uvicorn api:app --reload
"""

from api import app  # noqa: F401
