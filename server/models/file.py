"""File scanning data models."""

from pydantic import BaseModel


class ScannedFile(BaseModel):
    """Information about a scanned video or subtitle file."""

    filename: str
    path: str
    size: int
    extension: str
    mtime: str | None = None  # 修改时间 ISO 格式
    is_subtitle: bool = False  # True 表示该文件是孤立字幕文件（无对应视频）


class ScanRequest(BaseModel):
    """Request model for folder scanning."""

    folder_path: str
    exclude_scraped: bool = True  # 默认排除已刮削的文件


class ScanResponse(BaseModel):
    """Response model for folder scanning."""

    folder_path: str
    total_files: int
    files: list[ScannedFile]
    scraped_count: int = 0  # 已刮削文件数量（被排除的）


class DirectoryEntry(BaseModel):
    """Information about a directory entry."""

    name: str
    path: str
    is_dir: bool
    size: int | None = None  # 文件大小（字节），目录为 None
    mtime: str | None = None  # 修改时间 ISO 格式


class BrowseRequest(BaseModel):
    """Request model for directory browsing."""

    path: str = ""
    page: int = 1
    page_size: int = 20


class BrowseResponse(BaseModel):
    """Response model for directory browsing."""

    current_path: str
    parent_path: str | None
    entries: list[DirectoryEntry]
    total: int = 0  # 总条目数
    page: int = 1
    page_size: int = 20
