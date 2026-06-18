"""Vercel serverless entry point.

Vercel's Python runtime serves the ASGI `app` exported here. All /api/* routes are
rewritten to this function by vercel.json; the backend package is bundled via
includeFiles. Set SERVERLESS=true in the Vercel project env.
"""
import os
import sys

# Make the backend package importable from the repo's /backend directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402  (ASGI app Vercel will serve)
