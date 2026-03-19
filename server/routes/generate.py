from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..event_consumer import start_event_consumer

router = APIRouter(prefix="/api")


@router.post("/generate")
async def generate(request: Request) -> JSONResponse:
    registry = request.app.state.registry
    session = request.app.state.session

    if registry.has_active_job():
        return JSONResponse({"error": "A job is already running"}, status_code=409)

    settings = await request.json()
    config = request.app.state.config

    settings.setdefault("output_dir", str(config.output_dir))

    session_job = session.submit_task(settings)
    entry = registry.create(session_job)

    start_event_consumer(job=session_job, job_id=entry.job_id, registry=registry)

    return JSONResponse({"job_id": entry.job_id}, status_code=202)
