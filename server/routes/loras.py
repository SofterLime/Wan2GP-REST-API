from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)

LORA_EXTENSIONS = frozenset({".safetensors", ".pt", ".pth", ".ckpt", ".bin"})


def _scan_lora_directory(lora_dir: Path) -> list[dict]:
    """Scan directory for LoRA files and return metadata entries."""
    if not lora_dir.is_dir():
        return []

    entries = []
    for f in sorted(lora_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() not in LORA_EXTENSIONS:
            continue
        stem = f.stem
        display_name = stem.replace("_", " ").replace("-", " ")
        arch_hints = _infer_architectures(stem)
        entries.append({
            "filename": f.name,
            "display_name": display_name,
            "compatible_architectures": arch_hints,
        })
    return entries


def _infer_architectures(stem: str) -> list[str]:
    """Best-effort architecture inference from filename conventions."""
    lower = stem.lower()
    archs = []
    if "wan" in lower:
        if "2.2" in lower or "2_2" in lower or "22" in lower:
            archs.append("wan_2_2")
        if "2.1" in lower or "2_1" in lower or "21" in lower:
            archs.append("wan_2_1")
        if not archs:
            archs.extend(["wan_2_1", "wan_2_2"])
    if "ltx" in lower:
        archs.append("ltx2_22B")
    if "flux" in lower:
        archs.append("pi_flux")
    if not archs:
        archs.extend(["wan_2_1", "wan_2_2"])
    return archs


def _get_lora_directory(wgp: object) -> Path:
    """Resolve the LoRA directory from WanGP runtime."""
    lora_dir = getattr(wgp, "lora_dir", None)
    if lora_dir and Path(lora_dir).is_dir():
        return Path(lora_dir)

    data_dir = getattr(wgp, "data_dir", None)
    if data_dir:
        candidate = Path(data_dir) / "loras"
        if candidate.is_dir():
            return candidate

    base = getattr(wgp, "base_dir", None) or getattr(wgp, "root_dir", None)
    if base:
        candidate = Path(base) / "loras"
        if candidate.is_dir():
            return candidate

    return Path("loras")


def _get_model_architecture(wgp: object, model_type: str) -> str | None:
    """Get architecture for a given model_type."""
    get_def = getattr(wgp, "get_model_def", None)
    if get_def is None:
        return None
    md = get_def(model_type)
    if md is None:
        return None
    return md.get("architecture", "")


@router.get("/loras")
async def get_loras(
    request: Request,
    model_type: str | None = Query(None, description="Filter LoRAs by compatible model type"),
) -> JSONResponse:
    session = request.app.state.session
    try:
        runtime = session._ensure_runtime()
        wgp = runtime.module
    except Exception:
        return JSONResponse([])

    lora_dir = _get_lora_directory(wgp)
    entries = _scan_lora_directory(lora_dir)

    if model_type:
        arch = _get_model_architecture(wgp, model_type)
        if arch:
            entries = [
                e for e in entries
                if not e["compatible_architectures"]
                or any(arch.startswith(a) or a.startswith(arch) for a in e["compatible_architectures"])
            ]

    return JSONResponse(entries)
