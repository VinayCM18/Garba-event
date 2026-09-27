"""
api/index.py — Vercel Python Serverless Function entry point.

Vercel routes all /api/* requests here. This file imports the FastAPI ASGI
app from the backend package and exposes it to Vercel's Python runtime.
"""
import sys
import os

# ---------------------------------------------------------------------------
# Make the backend package importable from the Vercel function root.
# Vercel's working directory is the repository root, so we add
# <root>/backend to sys.path so that `from app.xxx import ...` works.
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")

if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# Change into the backend directory so relative paths (e.g. SQLite DB path,
# uploads directory) resolve correctly relative to backend/.
os.chdir(_BACKEND)

# ---------------------------------------------------------------------------
# Import the FastAPI app — Vercel's Python runtime uses the ASGI interface.
# ---------------------------------------------------------------------------
from app.main import app  # noqa: E402  (import after sys.path manipulation)

# Vercel expects the ASGI app to be assigned to `app` at module level.
__all__ = ["app"]
