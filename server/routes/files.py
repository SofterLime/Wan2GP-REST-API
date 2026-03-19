from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(prefix="/api")

CONTENT_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
}


@router.get("/files/{filename}", response_model=None)
async def get_file(filename: str, request: Request) -> FileResponse | JSONResponse:
    config = request.app.state.config

    safe_name = Path(filename).name
    if safe_name != filename:
        return JSONResponse({"error": "Invalid filename"}, status_code=400)

    for search_dir in (config.output_dir, config.upload_dir):
        candidate = search_dir / filename
        if candidate.is_file():
            media_type = CONTENT_TYPES.get(candidate.suffix.lower(), "application/octet-stream")
            return FileResponse(candidate, media_type=media_type, filename=filename)

    return JSONResponse({"error": "File not found"}, status_code=404)
