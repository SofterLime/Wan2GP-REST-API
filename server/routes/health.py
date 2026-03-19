from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")


@router.get("/health")
async def health(request: Request) -> dict:
    registry = request.app.state.registry
    active = registry.get_active()
    return {
        "status": "ok",
        "gpu_available": True,
        "active_job": active.job_id if active else None,
    }
