from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# New Modules
from models import InputRequest, RunArtifact
from orchestrator import Orchestrator
from database import init_db, get_recent_runs

app = FastAPI(title="Eklavya AI Assessment Engine")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Orchestrator
orchestrator = Orchestrator()

@app.on_event("startup")
def startup_event():
    init_db()

# --- Health Check ---
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# --- API Endpoints ---


@app.post("/generate", response_model=RunArtifact)
async def generate_assessment(request: InputRequest):
    """
    Triggers the full AI pipeline:
    Generator -> Reviewer -> (Refiner loop) -> Tagger -> Persistence
    """
    try:
        print(f"\n=== NEW REQUEST: {request.topic} (Grade {request.grade}) ===")
        result = await orchestrator.run_pipeline(request.grade, request.topic, user_id=request.user_id)
        print(f"=== PIPELINE COMPLETE: {result.final.status} ===\n")
        return result
    except Exception as e:
        import traceback
        with open("error.log", "w") as f:
            f.write(f"=== EXCEPTION ===\n")
            f.write(f"{type(e).__name__}: {str(e)}\n\n")
            f.write(traceback.format_exc())
        print(f"\n❌ ENDPOINT EXCEPTION: {type(e).__name__}: {str(e)}")
        print("Full traceback written to error.log")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history", response_model=List[RunArtifact])
def get_history(user_id: Optional[str] = None, limit: int = 10):
    """
    Returns the most recent run artifacts from the database, optionally filtered by user_id.
    """
    return get_recent_runs(limit, user_id=user_id)

import os

# --- Static Files (UI) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/style.css")
async def get_css():
    return FileResponse(os.path.join(BASE_DIR, 'style.css'), media_type="text/css")

@app.get("/script.js")
async def get_js():
    return FileResponse(os.path.join(BASE_DIR, 'script.js'), media_type="application/javascript")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(BASE_DIR, 'index.html'))
