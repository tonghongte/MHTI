"""Parser data models."""

from pydantic import BaseModel


class ParsedInfo(BaseModel):
    """Parsed episode information from filename."""

    original_filename: str
    series_name: str | None = None
    season: int | None = None
    episode: int | None = None
    episode_title: str | None = None
    year: int | None = None
    tmdb_id: int | None = None  # 从路径中提取的 TMDB ID
    is_parsed: bool = False
    confidence: float = 0.0


class ParseRequest(BaseModel):
    """Request model for filename parsing."""

    filename: str
    filepath: str | None = None


class BatchParseRequest(BaseModel):
    """Request model for batch filename parsing."""

    files: list[ParseRequest]


class ParseResponse(BaseModel):
    """Response model for filename parsing."""

    result: ParsedInfo


class BatchParseResponse(BaseModel):
    """Response model for batch filename parsing."""

    results: list[ParsedInfo]
    success_rate: float
