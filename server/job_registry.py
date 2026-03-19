from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class JobEntry:
    job_id: str
    session_job: Any
    status: str = "running"
    latest_progress: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


class JobRegistry:
    def __init__(self, *, ttl_seconds: int = 3600) -> None:
        self._jobs: dict[str, JobEntry] = {}
        self._lock = Lock()
        self._ttl_seconds = ttl_seconds

    def create(self, session_job: Any) -> JobEntry:
        job_id = uuid.uuid4().hex
        entry = JobEntry(job_id=job_id, session_job=session_job)
        with self._lock:
            self._jobs[job_id] = entry
        return entry

    def get(self, job_id: str) -> JobEntry | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_active(self) -> JobEntry | None:
        with self._lock:
            for entry in self._jobs.values():
                if entry.status == "running":
                    return entry
        return None

    def update_progress(self, job_id: str, progress: dict[str, Any]) -> None:
        with self._lock:
            entry = self._jobs.get(job_id)
            if entry:
                entry.latest_progress = progress

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            entry = self._jobs.get(job_id)
            if entry:
                entry.status = "completed"
                entry.result = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            entry = self._jobs.get(job_id)
            if entry:
                entry.status = "failed"
                entry.error = error

    def cancel(self, job_id: str) -> None:
        with self._lock:
            entry = self._jobs.get(job_id)
            if entry and entry.status == "running":
                entry.status = "cancelled"

    def has_active_job(self) -> bool:
        return self.get_active() is not None

    def cleanup_stale(self) -> list[str]:
        """Remove jobs older than TTL. Returns list of removed job IDs."""
        now = time.time()
        removed: list[str] = []
        with self._lock:
            stale_ids = [
                jid
                for jid, entry in self._jobs.items()
                if entry.status != "running" and (now - entry.created_at) > self._ttl_seconds
            ]
            for jid in stale_ids:
                del self._jobs[jid]
                removed.append(jid)
        return removed
