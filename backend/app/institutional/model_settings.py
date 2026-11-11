"""One canonical model selection; AI projections are updated atomically."""

import copy

from fastapi import HTTPException

from app.institutional.models import AI, Models

PROJECTIONS = (
    "model",
    "provider_models",
    "voice_models",
    "backup_model",
    "fallback_model",
    "backup_fallback_model",
)
MEDIA_PROJECTIONS = ("voice_model", "voice_id", "audio_model", "vision_model")


def project(ai, models):
    ai = copy.deepcopy(ai)
    selections = Models.model_validate(models).selections
    index = {(item.provider, item.category): item for item in selections}
    ai["provider_models"] = {
        item.provider: item.selected_model
        for item in selections
        if item.category == "text"
    }
    ai["voice_models"] = {
        item.provider: {"model": item.selected_model, "voice_id": item.voice_id}
        for item in selections
        if item.category == "voice"
    }

    def selected(provider, category):
        item = index.get((provider, category))
        return item.selected_model if item else ""

    ai["model"] = selected(ai["provider"], "text")
    ai["backup_model"] = selected(ai.get("backup_provider"), "text")
    fallbacks = ai.get("model_fallbacks_json", {})
    ai["fallback_model"] = next(iter(fallbacks.get(ai["provider"], [])), "")
    ai["backup_fallback_model"] = (
        next(iter(fallbacks.get(ai.get("backup_provider"), [])), "")
        if ai.get("backup_provider")
        else ""
    )
    media = ai["media"]
    media["voice_model"] = selected(media["voice_provider"], "voice")
    voice = index.get((media["voice_provider"], "voice"))
    media["voice_id"] = voice.voice_id if voice else ""
    media["audio_model"] = selected(media["audio_provider"], "audio")
    media["vision_model"] = selected(ai["vision_analysis_provider"], "vision")
    return AI.model_validate(ai).model_dump(mode="json")


def validate_projection(document, models):
    result = project(document, models)
    for key in PROJECTIONS:
        if document.get(key) != result[key]:
            raise HTTPException(422, "model_selection_owned_by_providers")
    for key in MEDIA_PROJECTIONS:
        if document.get("media", {}).get(key) != result["media"][key]:
            raise HTTPException(422, "model_selection_owned_by_providers")
    return result


def effective_limits(document):
    requested = AI.model_validate(document)
    maximum = min(max(requested.max_tokens, 200), 8000)
    if requested.human_reply_style_enabled:
        maximum = min(maximum, min(max(requested.output_tokens, 200), 2000))
    return {
        "max_tokens": maximum,
        "split_enabled": requested.split_responses and requested.chars_per_message > 0,
        "provider_operations_available": False,
    }


def chunks(text, document):
    settings = AI.model_validate(document)
    if not settings.split_responses or settings.chars_per_message <= 0:
        return [text] if text else []
    return [
        text[index : index + settings.chars_per_message]
        for index in range(0, len(text), settings.chars_per_message)
    ]
