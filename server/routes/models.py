from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api")

_IMAGE_ARCHITECTURES = frozenset({
    "z_image", "qwen_image", "pi_flux",
})


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

    for model_type in displayed:
        model_def = get_def(model_type)
        if model_def is None:
            continue

        architecture = model_def.get("architecture", "")
        name = model_def.get("name", model_type)
        is_audio = model_def.get("audio_only", False)
        if is_audio:
            continue

        entry: dict = {
            "model_type": model_type,
            "name": name,
            "architecture": architecture,
        }

        if _is_image_architecture(architecture):
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
