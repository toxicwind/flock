from fastapi import APIRouter, HTTPException
import json
import os
from typing import Dict, Any

router = APIRouter(prefix="/resume", tags=["resume"])

RESUME_PATH = os.path.join(os.path.dirname(__file__), "../../src/pages/resume/resume.json")

def load_resume_data() -> Dict[str, Any]:
    try:
        with open(RESUME_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Resume data file not found")

@router.get("/")
async def get_resume():
    return load_resume_data()

@router.get("/experience")
async def get_experience():
    data = load_resume_data()
    return data.get("experience", [])

@router.get("/projects")
async def get_projects():
    data = load_resume_data()
    return data.get("projects", [])

@router.get("/skills")
async def get_skills():
    data = load_resume_data()
    return data.get("skills", {})
