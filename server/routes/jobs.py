from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")


@router.get("/jobs/{job_id}/progress")
async def job_progress(job_id: str, request: Request) -> JSONResponse:
    registry = request.app.state.registry
    entry = registry.get(job_id)
    if not entry:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    if entry.status == "completed":
        return JSONResponse({"status": "completed", "phase": "done", "progress": 100})

    if entry.status == "failed":
        return JSONResponse({"status": "failed", "error": entry.error or "Unknown error"})

    if entry.status == "cancelled":
        return JSONResponse({"status": "cancelled"})

    progress = entry.latest_progress
    return JSONResponse({
        "status": "running",
        "phase": progress.get("phase", "starting"),
        "progress": progress.get("progress", 0),
        "current_step": progress.get("current_step"),
        "total_steps": progress.get("total_steps"),
    })


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, request: Request) -> JSONResponse:
    registry = request.app.state.registry
    entry = registry.get(job_id)
    if not entry:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    if entry.status != "running":
        return JSONResponse({"error": "Job is not running"}, status_code=409)

    entry.session_job.cancel()
    registry.cancel(job_id)
    return JSONResponse({"status": "cancelling"})


@router.get("/jobs/{job_id}/result")
async def job_result(job_id: str, request: Request) -> JSONResponse:
    registry = request.app.state.registry
    entry = registry.get(job_id)
    if not entry:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    if entry.status == "running":
        return JSONResponse({"status": "running", "message": "Job is still in progress"}, status_code=202)

    if entry.status == "failed":
        return JSONResponse({"status": "failed", "error": entry.error}, status_code=200)

    if entry.status == "cancelled":
        return JSONResponse({"status": "cancelled"}, status_code=200)

    result = entry.result or {}
    files = [
        {"filename": f.rsplit("/", 1)[-1] if "/" in f else f, "download_url": f"/api/files/{f.rsplit('/', 1)[-1] if '/' in f else f}"}
        for f in result.get("generated_files", [])
    ]
    return JSONResponse({
        "success": result.get("success", False),
        "files": files,
        "total_tasks": result.get("total_tasks", 0),
        "successful_tasks": result.get("successful_tasks", 0),
    })
