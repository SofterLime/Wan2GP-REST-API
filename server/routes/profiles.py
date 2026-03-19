from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)

_PROFILE_VRAM_MAP = {
    1: 16,
    2: 24,
    3: 32,
    4: 48,
    5: 80,
}

_PROFILE_NAMES = {
    1: "16GB Lite",
    2: "24GB Fast",
    3: "32GB Standard",
    4: "48GB Quality",
    5: "80GB Max",
}


def _build_profiles(wgp: object, displayed_model_types: list[str]) -> list[dict]:
    """Build profile list from WanGP runtime state."""
    get_def = getattr(wgp, "get_model_def", None)
    profiles_config = getattr(wgp, "server_config", {})
    if isinstance(profiles_config, dict):
        profiles_config = profiles_config
    else:
        profiles_config = {}

    managed_profiles = getattr(wgp, "mmgp_profiles", None)
    if managed_profiles and isinstance(managed_profiles, dict):
        result = []
        for pid_str, pdata in managed_profiles.items():
            pid = int(pid_str) if isinstance(pid_str, str) and pid_str.isdigit() else pid_str
            compatible = []
            for mt in displayed_model_types:
                md = get_def(mt) if get_def else None
                if md is None:
                    continue
                if md.get("audio_only", False):
                    continue
                model_profiles = md.get("mmgp_profiles", [])
                if pid in model_profiles or not model_profiles:
                    compatible.append(mt)
            name = pdata.get("name", _PROFILE_NAMES.get(pid, f"Profile {pid}"))
            vram = pdata.get("vram_gb", _PROFILE_VRAM_MAP.get(pid, 0))
            result.append({
                "id": str(pid),
                "name": name,
                "vram_gb": vram,
                "compatible_model_types": compatible,
            })
        return result

    all_model_types = [
        mt for mt in displayed_model_types
        if get_def and get_def(mt) and not get_def(mt).get("audio_only", False)
    ]

    profiles = []
    for pid in sorted(_PROFILE_NAMES.keys()):
        compatible = []
        for mt in all_model_types:
            md = get_def(mt) if get_def else None
            if md is None:
                continue
            model_profiles = md.get("mmgp_profiles", [])
            if pid in model_profiles or not model_profiles:
                compatible.append(mt)
        if compatible:
            profiles.append({
                "id": str(pid),
                "name": _PROFILE_NAMES[pid],
                "vram_gb": _PROFILE_VRAM_MAP[pid],
                "compatible_model_types": compatible,
            })

    if not profiles:
        profiles.append({
            "id": "default",
            "name": "Default",
            "vram_gb": 0,
            "compatible_model_types": all_model_types,
        })

    return profiles


@router.get("/profiles")
async def get_profiles(request: Request) -> JSONResponse:
    session = request.app.state.session
    try:
        runtime = session._ensure_runtime()
        wgp = runtime.module
    except Exception:
        return JSONResponse([{"id": "default", "name": "Default", "vram_gb": 0, "compatible_model_types": []}])

    displayed = getattr(wgp, "displayed_model_types", [])
    profiles = _build_profiles(wgp, displayed)
    return JSONResponse(profiles)
