"""Vercel Python entry point.

Vercel serves the ASGI `app` exported here. We add the backend root to sys.path
so imports like `from main import app` and `from agents...` resolve when the
function runs from the /api directory.
"""
import os
import sys

# Ensure the backend root (parent of /api) is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402

# Vercel's @vercel/python runtime detects and serves this ASGI `app`.
