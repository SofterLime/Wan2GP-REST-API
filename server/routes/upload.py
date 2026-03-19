from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile

router = APIRouter(prefix="/api")


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile) -> dict:
    config = request.app.state.config
    ext = Path(file.filename or "file").suffix or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = config.upload_dir / unique_name

    content = await file.read()
    dest.write_bytes(content)

    server_path = str(dest.resolve())
    return {"filename": unique_name, "server_path": server_path}
