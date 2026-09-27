"""Vercel serverless entrypoint: exposes the FastAPI app as a serverless function.

Vercel project settings for the backend: Root Directory = `backend`.
Requires `DATABASE_URL` (Neon/Supabase Postgres) — SQLite cannot persist on serverless.
Tables + seed data are created at import (see app/main.py), so no startup hook is needed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import Mangum  # noqa: E402

from app.main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
