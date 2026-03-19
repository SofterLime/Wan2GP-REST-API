from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ServerConfig:
    host: str = field(default_factory=lambda: os.environ.get("WANGP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("WANGP_PORT", "8100")))
    api_key: str = field(default_factory=lambda: os.environ.get("WANGP_API_KEY", ""))
    upload_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("WANGP_UPLOAD_DIR", "uploads"))
    )
    output_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("WANGP_OUTPUT_DIR", "output"))
    )
    job_ttl_seconds: int = field(
        default_factory=lambda: int(os.environ.get("WANGP_JOB_TTL", "3600"))
    )

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> ServerConfig:
    config = ServerConfig()
    config.ensure_dirs()
    return config
