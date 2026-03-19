from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

from shared.api import WanGPSession

from .app import create_app
from .config import load_config
from .job_registry import JobRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config()
    logger.info("Starting Wan2GP REST API on %s:%d", config.host, config.port)

    logger.info("Initializing WanGP session...")
    session = WanGPSession(
        output_dir=config.output_dir,
        console_output=True,
    )
    session.ensure_ready()
    logger.info("WanGP session ready")

    registry = JobRegistry(ttl_seconds=config.job_ttl_seconds)
    app = create_app(config=config, session=session, registry=registry)

    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


if __name__ == "__main__":
    main()
