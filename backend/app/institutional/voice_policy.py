"""Explicit voice policy. Conversation quotas live in SQL, never in this model."""

import math
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

GreetingTone = Literal["inherit", "warm", "calm", "upbeat"]


class VoiceAmbience(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    enabled: bool = False
    voice_volume: float = Field(default=1.0, ge=0.2, le=1.5)
    office_volume: float = Field(default=0.12, ge=0, le=1)
    typing_volume: float = Field(default=0.16, ge=0, le=1)
    ducking: bool = True


class VoiceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=100)
    voice_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,200}$")
    model_id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,200}$")
    active: bool = True
    delivery: Literal["conversational", "calm", "expressive", "neutral"] = "conversational"
    allow_reactions: bool = False
    speech_instructions: str = Field(default="", max_length=1000)
    stability: float | None = Field(default=None, ge=0, le=1)
    similarity_boost: float = Field(default=0.75, ge=0, le=1)
    language_code: str = Field(default="", pattern=r"^(?:[a-z]{2})?$")
    greeting_tone: GreetingTone = "inherit"
    ambience: VoiceAmbience = Field(default_factory=VoiceAmbience)
    agent_ids: list[str] = Field(default_factory=list, max_length=50)
    schools: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def assignments(self):
        self.name = self.name.strip()
        if self.model_id == "eleven_multilingual_v2" and self.language_code:
            raise ValueError("voice_language_unsupported")
        if not self.name or any(ord(ch) < 32 for ch in self.name):
            raise ValueError("voice_invalid_profile")
        self.agent_ids = [str(UUID(value)) for value in self.agent_ids]
        self.schools = [value.strip() for value in self.schools]
        if any(not value or len(value) > 100 for value in self.schools):
            raise ValueError("voice_invalid_school")
        if len(set(self.agent_ids)) != len(self.agent_ids) or len(set(self.schools)) != len(self.schools):
            raise ValueError("voice_duplicate_assignment")
        return self


class VoicePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool = False
    scope: Literal["selected_conversations", "all"] = "selected_conversations"
    conversation_ids: list[str] = Field(default_factory=list, max_length=50)
    max_audios_per_conversation: int = Field(default=3, ge=0, le=100)
    mode: Literal["voice_notes", "long_explanations", "voice_notes_or_long", "voice_notes_and_long"] = "voice_notes_or_long"
    long_reply_min_chars: int = Field(default=400, ge=120, le=2000)
    max_text_chars: int = Field(default=2000, ge=120, le=3000)
    max_audio_seconds: int = Field(default=60, ge=0, le=300)
    daily_character_limit: int = Field(default=20000, ge=0, le=10000000)
    default_profile_id: str = Field(default="", max_length=64)
    profiles: list[VoiceProfile] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def valid_profiles(self):
        self.conversation_ids = [str(UUID(value)) for value in self.conversation_ids]
        if len(set(self.conversation_ids)) != len(self.conversation_ids):
            raise ValueError("voice_duplicate_conversation")
        if self.enabled and self.scope == "selected_conversations" and not self.conversation_ids:
            raise ValueError("voice_pilot_conversation_required")
        ids, agents, schools = set(), set(), set()
        for profile in self.profiles:
            if profile.id in ids:
                raise ValueError("voice_duplicate_profile")
            ids.add(profile.id)
            if profile.active:
                if agents.intersection(profile.agent_ids) or schools.intersection(value.casefold() for value in profile.schools):
                    raise ValueError("voice_duplicate_assignment")
                agents.update(profile.agent_ids)
                schools.update(value.casefold() for value in profile.schools)
        if self.default_profile_id and self.default_profile_id not in ids:
            raise ValueError("voice_default_profile_missing")
        default = next((p for p in self.profiles if p.id == self.default_profile_id and p.active), None)
        if self.enabled and not default:
            raise ValueError("voice_default_profile_missing")
        if self.max_text_chars < self.long_reply_min_chars:
            raise ValueError("voice_invalid_threshold")
        return self

    def allows(self, conversation):
        return self.scope == "all" or str(conversation).lower() in self.conversation_ids


def reason(policy: VoicePolicy, text: str, incoming_voice: bool, used: int):
    if not policy.enabled:
        return "voice_paused"
    if used >= policy.max_audios_per_conversation:
        return "voice_conversation_limit"
    if len(text) > policy.max_text_chars:
        return "voice_text_too_large"
    if policy.max_audio_seconds and estimate_seconds(text) > policy.max_audio_seconds:
        return "voice_duration_estimated_exceeded"
    long = len(text.strip()) >= policy.long_reply_min_chars
    eligible = {
        "voice_notes": incoming_voice,
        "long_explanations": long,
        "voice_notes_or_long": incoming_voice or long,
        "voice_notes_and_long": incoming_voice and long,
    }[policy.mode]
    return None if text.strip() and eligible else "voice_text_preferred"


def estimate_seconds(text: str):
    """Conservative estimate, not a provider guarantee; actual audio is checked too."""
    words = len(re.findall(r"\S+", text))
    pauses = len(re.findall(r"[.,;:!?…\n]", text))
    return math.ceil(max(words / 2, len(text) / 12) + pauses * 0.4 + 2)


def choose_profile(policy: VoicePolicy, agent: str | None, schools=(), pinned=None, selected_profile=""):
    active = [p for p in policy.profiles if p.active]
    if pinned:
        # Pin the actual voice/model too, not just an editable display name.
        return next((p for p in active if p.id == pinned.get("id") and p.voice_id == pinned.get("voice_id") and p.model_id == pinned.get("model_id")), None)
    if selected_profile:
        # A missing explicit choice falls back to text, never a surprise voice.
        return next((p for p in active if p.id == selected_profile), None)
    assigned = next((p for p in active if agent in p.agent_ids), None)
    if assigned:
        return assigned
    matches = [p for p in active if {v.casefold() for v in schools}.intersection(v.casefold() for v in p.schools)]
    if len(matches) == 1:
        return matches[0]
    return next((p for p in active if p.id == policy.default_profile_id), None)
