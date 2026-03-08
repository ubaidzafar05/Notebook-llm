from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PodcastTurn(BaseModel):
    speaker: str = Field(pattern="^(HOST|ANALYST)$")
    text: str = Field(min_length=1, max_length=1200)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Turn text cannot be empty")
        return cleaned


class PodcastScript(BaseModel):
    turns: list[PodcastTurn] = Field(min_length=12, max_length=20)

    @field_validator("turns")
    @classmethod
    def validate_speaker_mix(cls, turns: list[PodcastTurn]) -> list[PodcastTurn]:
        speakers = {turn.speaker for turn in turns}
        if speakers != {"HOST", "ANALYST"}:
            raise ValueError("Script must contain HOST and ANALYST turns")
        return turns

    def as_text(self) -> str:
        return "\n".join(f"{turn.speaker}: {turn.text}" for turn in self.turns)
