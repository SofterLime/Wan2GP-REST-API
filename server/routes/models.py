from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)

_IMAGE_ARCHITECTURES = frozenset({
    "z_image", "qwen_image", "pi_flux",
})

_COMMON_VIDEO_PARAMS: list[dict[str, Any]] = [
    {"key": "guidance_scale", "label": "Guidance Scale", "type": "number", "default": 7.5, "min": 1.0, "max": 30.0, "step": 0.5},
    {"key": "num_inference_steps", "label": "Inference Steps", "type": "number", "default": 30, "min": 1, "max": 100, "step": 1},
    {"key": "negative_prompt", "label": "Negative Prompt", "type": "string", "default": "", "placeholder": "Things to avoid..."},
    {"key": "seed", "label": "Seed", "type": "number", "default": -1, "min": -1, "max": 2147483647, "step": 1},
    {"key": "use_teacache", "label": "TeaCache", "type": "boolean", "default": True},
]

_COMMON_IMAGE_PARAMS: list[dict[str, Any]] = [
    {"key": "guidance_scale", "label": "Guidance Scale", "type": "number", "default": 7.5, "min": 1.0, "max": 30.0, "step": 0.5},
    {"key": "num_inference_steps", "label": "Inference Steps", "type": "number", "default": 30, "min": 1, "max": 100, "step": 1},
    {"key": "negative_prompt", "label": "Negative Prompt", "type": "string", "default": "", "placeholder": "Things to avoid..."},
    {"key": "seed", "label": "Seed", "type": "number", "default": -1, "min": -1, "max": 2147483647, "step": 1},
]


def _is_image_architecture(architecture: str) -> bool:
    return any(architecture.startswith(prefix) for prefix in _IMAGE_ARCHITECTURES)


def _extract_image_ref_roles(model_def: dict) -> list[str]:
    irc = model_def.get("image_ref_choices", {})
    choices = irc.get("choices", [])
    letters = set()
    for choice in choices:
        if isinstance(choice, (list, tuple)) and len(choice) >= 2:
            letters.update(choice[1])
    roles: list[str] = []
    if "I" in letters:
        roles.append("character")
    if "K" in letters:
        roles.append("environment")
    return roles


def _load_model_settings(wgp: object) -> dict[str, Any]:
    """Try to load _settings.json from models directory."""
    for attr in ("models_dir", "data_dir", "base_dir", "root_dir"):
        base = getattr(wgp, attr, None)
        if base:
            settings_path = Path(base) / "models" / "_settings.json"
            if not settings_path.is_file():
                settings_path = Path(base) / "_settings.json"
            if settings_path.is_file():
                try:
                    return json.loads(settings_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
    return {}


def _build_parameters(model_type: str, model_def: dict, is_image: bool, settings_data: dict) -> list[dict[str, Any]]:
    """Build parameter definitions for a model from its definition and settings."""
    base_params = list(_COMMON_IMAGE_PARAMS if is_image else _COMMON_VIDEO_PARAMS)

    model_settings = settings_data.get(model_type, {})
    if isinstance(model_settings, dict):
        for key, val in model_settings.items():
            if key.startswith("_") or key in ("name", "architecture", "model_type"):
                continue
            existing = next((p for p in base_params if p["key"] == key), None)
            if existing:
                if isinstance(val, dict):
                    if "default" in val:
                        existing["default"] = val["default"]
                    if "min" in val:
                        existing["min"] = val["min"]
                    if "max" in val:
                        existing["max"] = val["max"]
                else:
                    existing["default"] = val
            elif isinstance(val, bool):
                base_params.append({"key": key, "label": key.replace("_", " ").title(), "type": "boolean", "default": val})
            elif isinstance(val, (int, float)):
                base_params.append({"key": key, "label": key.replace("_", " ").title(), "type": "number", "default": val})
            elif isinstance(val, str):
                base_params.append({"key": key, "label": key.replace("_", " ").title(), "type": "string", "default": val})

    return base_params


def _build_image_capabilities(model_def: dict, architecture: str) -> dict[str, Any]:
    """Build capabilities block for image models."""
    supports_ref = False
    ref_roles: list[str] = []

    ipt = model_def.get("image_prompt_types_allowed", "")
    if ipt:
        supports_ref = True

    irc = model_def.get("image_ref_choices", {})
    if irc:
        supports_ref = True
        choices = irc.get("choices", [])
        for choice in choices:
            if isinstance(choice, (list, tuple)) and len(choice) >= 2:
                for letter in choice[1]:
                    if letter == "I":
                        ref_roles.append("character")
                    elif letter == "K":
                        ref_roles.append("environment")

    if architecture.startswith("qwen_image"):
        supports_ref = True
        if not ref_roles:
            ref_roles = ["style", "composition"]
    elif architecture.startswith("pi_flux"):
        supports_ref = True
        if not ref_roles:
            ref_roles = ["style"]

    if not ref_roles and supports_ref:
        ref_roles = ["reference"]

    return {
        "supports_reference": supports_ref,
        "reference_roles": ref_roles,
    }


@router.get("/models")
async def get_models(request: Request) -> JSONResponse:
    session = request.app.state.session
    try:
        runtime = session._ensure_runtime()
        wgp = runtime.module
    except Exception:
        return JSONResponse({"video_models": [], "image_models": []})

    video_models: list[dict] = []
    image_models: list[dict] = []

    displayed = getattr(wgp, "displayed_model_types", [])
    get_def = getattr(wgp, "get_model_def", None)
    if get_def is None:
        return JSONResponse({"video_models": [], "image_models": []})

    settings_data = _load_model_settings(wgp)

    for model_type in displayed:
        model_def = get_def(model_type)
        if model_def is None:
            continue

        architecture = model_def.get("architecture", "")
        name = model_def.get("name", model_type)
        is_audio = model_def.get("audio_only", False)
        if is_audio:
            continue

        is_image = _is_image_architecture(architecture)

        entry: dict = {
            "model_type": model_type,
            "name": name,
            "architecture": architecture,
            "parameters": _build_parameters(model_type, model_def, is_image, settings_data),
        }

        if is_image:
            entry["capabilities"] = _build_image_capabilities(model_def, architecture)
            image_models.append(entry)
        else:
            ipt = model_def.get("image_prompt_types_allowed", "")
            ref_roles = _extract_image_ref_roles(model_def)
            entry["capabilities"] = {
                "i2v": "S" in ipt or len(ref_roles) > 0,
                "t2v": True,
                "image_prompt_types_allowed": ipt,
                "image_ref_roles": ref_roles,
                "one_image_ref_needed": model_def.get("one_image_ref_needed", False),
            }
            video_models.append(entry)

    return JSONResponse({"video_models": video_models, "image_models": image_models})
