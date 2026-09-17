from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import datetime as dt
import httpx
import re
import json
from enum import Enum

# Import logic from original script if possible, or reimplement
# For now, reimplementing core parts to be importable

router = APIRouter(prefix="/popmart", tags=["popmart"])

# --- Models ---
class ReconRequest(BaseModel):
    id_start: int = 3450
    id_end: int = 3650
    scan_collections: bool = False
    scan_brandip: bool = False
    scan_popnow: bool = False
    probe_cdn: bool = False

class ReconStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    results: Optional[List[Dict[str, Any]]] = None

# --- In-Memory Store (Replace with Redis later) ---
tasks: Dict[str, ReconStatus] = {}

# --- Logic adapted from oneoff_popmart.py ---
# (Simplified for API consumption)

async def mock_recon_task(task_id: str, req: ReconRequest):
    tasks[task_id].status = "running"
    
    # Simulate discovery
    await asyncio.sleep(2)
    tasks[task_id].progress = 0.2
    
    # Simulate processing
    await asyncio.sleep(2)
    tasks[task_id].progress = 0.5
    
    # Mock results
    results = [
        {
            "id": 101,
            "title": "Molly Space V3",
            "price": "US$15.00",
            "url": "https://global.popmart.com/us/products/101",
            "timestamp": dt.datetime.utcnow().isoformat()
        },
        {
            "id": 102,
            "title": "Labubu The Monsters",
            "price": "US$18.00",
            "url": "https://global.popmart.com/us/products/102",
            "timestamp": dt.datetime.utcnow().isoformat()
        }
    ]
    
    tasks[task_id].results = results
    tasks[task_id].progress = 1.0
    tasks[task_id].status = "completed"

@router.post("/recon", response_model=ReconStatus)
async def start_recon(req: ReconRequest, background_tasks: BackgroundTasks):
    task_id = f"task_{dt.datetime.utcnow().timestamp()}"
    tasks[task_id] = ReconStatus(task_id=task_id, status="queued", progress=0.0)
    
    from services.mildlyawesome.scrapers.popmart import PopmartScraper
    
    async def run_scraper_task(tid, request_params):
        tasks[tid].status = "running"
        scraper = PopmartScraper()
        try:
            results = await scraper.run_recon_task(request_params.dict())
            tasks[tid].results = results["items"]
            tasks[tid].progress = 1.0
            tasks[tid].status = "completed"
        except Exception as e:
            tasks[tid].status = "failed"
            # In real app store error
    
    background_tasks.add_task(run_scraper_task, task_id, req)
    
    return tasks[task_id]

@router.get("/recon/{task_id}", response_model=ReconStatus)
async def get_recon_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@router.get("/drops/latest")
async def get_latest_drops():
    """Get latest detected drops (Mock)"""
    return [
        {"id": 3601, "name": "Skullpanda Image of Reality", "status": "In Stock"},
        {"id": 3602, "name": "Dimoo Dating Series", "status": "Low Stock"}
    ]
