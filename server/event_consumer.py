from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.api import SessionJob

    from .job_registry import JobRegistry

logger = logging.getLogger(__name__)


def start_event_consumer(
    *,
    job: SessionJob,
    job_id: str,
    registry: JobRegistry,
) -> threading.Thread:
    def _consume() -> None:
        try:
            for event in job.events.iter(timeout=0.5):
                if event.kind == "progress":
                    registry.update_progress(job_id, {
                        "phase": event.data.phase,
                        "progress": event.data.progress,
                        "current_step": event.data.current_step,
                        "total_steps": event.data.total_steps,
                        "status_text": event.data.status,
                    })
                elif event.kind == "preview":
                    registry.update_progress(job_id, {
                        "phase": event.data.phase,
                        "progress": event.data.progress,
                        "current_step": event.data.current_step,
                        "total_steps": event.data.total_steps,
                        "has_preview": True,
                    })
                elif event.kind == "completed":
                    result = event.data
                    registry.complete(job_id, {
                        "success": result.success,
                        "generated_files": result.generated_files,
                        "total_tasks": result.total_tasks,
                        "successful_tasks": result.successful_tasks,
                        "failed_tasks": result.failed_tasks,
                        "errors": [
                            {"message": e.message, "stage": e.stage}
                            for e in result.errors
                        ],
                    })
                    return
                elif event.kind == "error":
                    registry.fail(job_id, event.data.message)
                    return
        except Exception:
            logger.exception("Event consumer crashed for job %s", job_id)
            registry.fail(job_id, "Event consumer crashed unexpectedly")

    thread = threading.Thread(target=_consume, daemon=True, name=f"event-consumer-{job_id}")
    thread.start()
    return thread

