"""Data models for naming templates."""

from enum import Enum

from pydantic import BaseModel


class TemplateVariable(str, Enum):
    """Available template variables."""

    TITLE = "title"
    ORIGINAL_TITLE = "original_title"
    YEAR = "year"
    SEASON = "season"
    EPISODE = "episode"
    EPISODE_TITLE = "episode_title"
    AIR_DATE = "air_date"
    TMDB_ID = "tmdb_id"


class NamingTemplate(BaseModel):
    """File naming template configuration."""

    series_folder: str = "{title} ({year}) [tmdbid-{tmdb_id}]"
    season_folder: str = "Season {season}"
    episode_file: str = "{title} - S{season:02d}E{episode:02d} - {episode_title}"


class TemplatePreviewRequest(BaseModel):
    """Request for template preview."""

    template: str
    sample_data: dict | None = None


class TemplatePreviewResponse(BaseModel):
    """Response with preview result."""

    template: str
    preview: str
    valid: bool
    error: str | None = None


class TemplateValidationResult(BaseModel):
    """Result of template validation."""

    valid: bool
    error: str | None = None
    variables_found: list[str] = []
