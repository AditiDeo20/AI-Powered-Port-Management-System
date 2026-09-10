"""
Port Land Lease MMS — Backend API Entrypoint
===========================================
Modularized FastAPI backend incorporating:
  - tenant.py : Tenant authentication & dashboard REST APIs
  - admin.py  : Port Authority / Admin authentication & endpoints
  - database.py: PostgreSQL connection manager

Run:
    uvicorn main:app --reload --port 8000
"""

import os
import sys
from pathlib import Path as FilePath

# Ensure backend directory is in sys.path so modules (tenant, admin, database) import cleanly
_backend_dir = str(FilePath(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from tenant import tenant_router
from admin import admin_router
from cases import cases_router
from agenda_workflow import agenda_router, init_agenda_tables
from officer_ingestion import ingest_and_seed_officers
from workflow_routes import workflow_router

app = FastAPI(
    title="Port Land Lease MMS API",
    version="1.0.0",
    description="Port Land Lease Management System — Tenant & Admin Portals API.",
)

# Startup DB Schema Setup & Officer Ingestion
@app.on_event("startup")
def on_startup():
    try:
        init_agenda_tables()
        ingest_and_seed_officers()
    except Exception as exc:
        print(f"[Startup Warning] Could not complete initialization: {exc}")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include Modular Routers
app.include_router(tenant_router)
app.include_router(admin_router)
app.include_router(cases_router)
app.include_router(agenda_router)
app.include_router(workflow_router)

# The complete source-backed workflow interface is kept as a focused tool so
# the main AI assistant remains uncluttered.
app.mount("/workflow-tools", StaticFiles(directory=str(FilePath(__file__).resolve().parent / "workflows" / "static"), html=True), name="workflow-tools")

# Health Check Endpoint
@app.get("/health", tags=["Ops"])
async def health() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
