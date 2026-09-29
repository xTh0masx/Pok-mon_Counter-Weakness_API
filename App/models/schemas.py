from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    input_type: Literal["auto", "pokemon", "type"] = "auto"
    limit: int = Field(default=5, ge=1, le=10, strict=True)

    @field_validator("query", mode="before")
    @classmethod
    def normalize_query(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class Weakness(BaseModel):
    type: str
    multiplier: float


class Recommendation(BaseModel):
    name: str
    score: float
    reason: str


class AnalysisResponse(BaseModel):
    target: str
    target_types: list[str]
    weaknesses: list[Weakness]
    recommended_pokemon: list[Recommendation]
    source: Literal["pokeapi", "cache", "fallback"]
    cache_used: bool
    warnings: list[str]
