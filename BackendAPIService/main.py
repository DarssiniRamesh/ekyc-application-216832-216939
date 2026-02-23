"""
BackendAPIService entrypoint for the EKYC application.

Run locally:
    uvicorn main:app --reload --port 8000
"""

from app.main import app  # re-export for uvicorn
