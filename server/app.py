from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

from fastapi import FastAPI

from .auth import AuthMiddleware
from .routes.files import router as files_router
from .routes.generate import router as generate_router
from .routes.health import router as health_router
from .routes.jobs import router as jobs_router
from .routes.upload import router as upload_router

if TYPE_CHECKING:
    from shared.api import WanGPSession

    from .config import ServerConfig
    from .job_registry import JobRegistry

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_SECONDS = 300


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_cleanup_loop(app))
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _cleanup_loop(app: FastAPI) -> None:
    registry = app.state.registry
    config = app.state.config
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        removed = registry.cleanup_stale()
        for job_id in removed:
            logger.info("Cleaned up stale job %s", job_id)
            for d in (config.upload_dir, config.output_dir):
                for f in d.iterdir():
                    if f.name.startswith(job_id):
                        f.unlink(missing_ok=True)


def create_app(
    *,
    config: ServerConfig,
    session: WanGPSession,
    registry: JobRegistry,
) -> FastAPI:
    app = FastAPI(title="Wan2GP REST API", version="1.0.0", lifespan=_lifespan)

    app.state.config = config
    app.state.session = session
    app.state.registry = registry

    app.add_middleware(AuthMiddleware, api_key=config.api_key)

    app.include_router(health_router)
    app.include_router(upload_router)
    app.include_router(generate_router)
    app.include_router(jobs_router)
    app.include_router(files_router)

    return app
