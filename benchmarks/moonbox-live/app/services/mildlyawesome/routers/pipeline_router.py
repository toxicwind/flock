"""
Pipeline Manager Service
Wraps local tool scripts (like lv-images pipeline) into API endpoints

Features:
- Subprocess execution management
- Log streaming (via websockets in main orchestrator, or simpler polling here)
- Status tracking
"""

import asyncio
import os
import subprocess
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

PIPELINE_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../tools/lv-images/pipeline.mjs"))

class TaskStatus(BaseModel):
    id: str
    command: str
    status: str  # running, completed, failed
    start_time: str
    end_time: Optional[str] = None
    exit_code: Optional[int] = None
    logs: List[str] = []

# In-memory task store
tasks: Dict[str, TaskStatus] = {}

class PipelineRequest(BaseModel):
    command: str = "crawl"  # crawl, build, doctor
    mode: Optional[str] = "pages"
    label: Optional[str] = None

@router.post("/lv-images/run")
async def run_lv_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    """Trigger the lv-images pipeline"""
    
    if not os.path.exists(PIPELINE_SCRIPT):
        raise HTTPException(status_code=500, detail=f"Pipeline script not found at {PIPELINE_SCRIPT}")
    
    task_id = f"lv-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Construct args
    args = ["node", PIPELINE_SCRIPT, req.command]
    if req.mode:
        args.append(f"--mode={req.mode}")
    if req.label:
        args.append(f"--label={req.label}")
        
    tasks[task_id] = TaskStatus(
        id=task_id,
        command=f"pipeline.mjs {req.command}",
        status="running",
        start_time=datetime.now().isoformat(),
        logs=["Starting pipeline task..."]
    )
    
    background_tasks.add_task(execute_pipeline_task, task_id, args)
    
    return {"task_id": task_id, "status": "started"}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status and logs of a pipeline task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@router.get("/tasks")
async def list_tasks():
    """List all pipeline tasks"""
    return list(tasks.values())

async def execute_pipeline_task(task_id: str, args: List[str]):
    """Execute the pipeline subprocess"""
    task = tasks[task_id]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.dirname(PIPELINE_SCRIPT)) # Project root
        )
        
        # Read logs in real-time (simplification for async)
        # In a real system we'd consume streams more robustly
        stdout, stderr = await process.communicate()
        
        # Determine success
        task.exit_code = process.returncode
        task.end_time = datetime.now().isoformat()
        
        if stdout:
            task.logs.extend(stdout.decode().splitlines())
        if stderr:
            task.logs.extend(stderr.decode().splitlines())
            
        if process.returncode == 0:
            task.status = "completed"
            task.logs.append("Pipeline finished successfully")
        else:
            task.status = "failed"
            task.logs.append(f"Pipeline failed with exit code {process.returncode}")
            
    except Exception as e:
        task.status = "failed"
        task.end_time = datetime.now().isoformat()
        task.logs.append(f"Execution error: {str(e)}")

@router.get("/health")
async def health_check():
    return {"status": "ready", "script_path": PIPELINE_SCRIPT, "script_exists": os.path.exists(PIPELINE_SCRIPT)}
