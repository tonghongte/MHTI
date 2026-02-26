"""File scanning service for video file discovery."""

import os
import re
from pathlib import Path

from server.core.exceptions import (
    FolderNotFoundError,
    InvalidFolderError,
    PermissionDeniedError,
)
from server.models.file import DirectoryEntry, ScannedFile

# Supported video file extensions
SUPPORTED_VIDEO_EXTENSIONS: set[str] = {
    ".mp4",
    ".mkv",
    ".avi",
    ".wmv",
    ".mov",
    ".flv",
    ".rmvb",
    ".ts",
    ".m2ts",
    ".bdmv",
    ".webm",
    ".3gp",
    ".mpg",
    ".mpeg",
    ".vob",
    ".iso",
}

# Subtitle extensions to include in scan (only when they have S01E01 naming)
SUPPORTED_SUBTITLE_EXTENSIONS_FOR_SCAN: set[str] = {".ass", ".ssa", ".srt", ".vtt", ".sub"}

# Episode pattern for subtitle scan inclusion (e.g. S01E01, s1e2)
_SUBTITLE_EPISODE_RE = re.compile(r"[Ss]\d+[Ee]\d+")

# 禁止访问的系统目录（安全防护）
BLOCKED_PATHS = {
    "/etc", "/var", "/usr", "/bin", "/sbin", "/boot", "/root", "/proc", "/sys",
    "C:\Windows", "C:\Program Files", "C:\Program Files (x86)",
}


def _sanitize_path(path_str: str) -> Path:
    """
    Sanitize and validate path to prevent path traversal attacks.

    Args:
        path_str: Raw path string from user input.

    Returns:
        Sanitized Path object.

    Raises:
        InvalidFolderError: If path contains dangerous patterns.
    """
    if not path_str:
        return Path("")

    # 检查危险模式
    dangerous_patterns = ["..", "~", "\x00"]
    for pattern in dangerous_patterns:
        if pattern in path_str:
            raise InvalidFolderError(f"路径包含非法字符: {pattern}")

    # 规范化路径
    path = Path(path_str).resolve()

    # 检查是否在禁止目录中
    path_str_normalized = str(path).replace("\\", "/")
    for blocked in BLOCKED_PATHS:
        blocked_normalized = blocked.replace("\\", "/")
        if path_str_normalized.startswith(blocked_normalized):
            raise PermissionDeniedError(f"禁止访问系统目录: {blocked}")

    return path


class FileService:
    """Service for scanning folders and discovering video files."""

    def scan_folder(self, folder_path: str) -> list[ScannedFile]:
        """
        Scan a folder recursively for video files.

        Args:
            folder_path: Path to the folder to scan.

        Returns:
            List of ScannedFile objects representing discovered video files.

        Raises:
            FolderNotFoundError: If the folder does not exist.
            InvalidFolderError: If the path is not a directory.
            PermissionDeniedError: If access to the folder is denied.
        """
        # 路径安全验证
        path = _sanitize_path(folder_path)

        # Validate folder exists
        if not path.exists():
            raise FolderNotFoundError(folder_path)

        # Validate path is a directory
        if not path.is_dir():
            raise InvalidFolderError(folder_path)

        # Scan for video files
        try:
            return self._scan_recursive(path)
        except PermissionError as e:
            raise PermissionDeniedError(folder_path) from e

    def _scan_recursive(self, folder: Path) -> list[ScannedFile]:
        """
        Recursively scan a folder for video files.

        Args:
            folder: Path object of the folder to scan.

        Returns:
            List of ScannedFile objects.
        """
        from datetime import datetime

        video_files: list[ScannedFile] = []

        for item in folder.rglob("*"):
            if not item.is_file():
                continue

            ext = item.suffix.lower()
            stat = item.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()

            if ext in SUPPORTED_VIDEO_EXTENSIONS:
                video_files.append(
                    ScannedFile(
                        filename=item.name,
                        path=str(item.absolute()),
                        size=stat.st_size,
                        extension=ext,
                        mtime=mtime,
                        is_subtitle=False,
                    )
                )
            elif (
                ext in SUPPORTED_SUBTITLE_EXTENSIONS_FOR_SCAN
                and _SUBTITLE_EPISODE_RE.search(item.stem)
            ):
                # 仅包含含集号的字幕文件（如 S01E01.chs.ass）
                video_files.append(
                    ScannedFile(
                        filename=item.name,
                        path=str(item.absolute()),
                        size=stat.st_size,
                        extension=ext,
                        mtime=mtime,
                        is_subtitle=True,
                    )
                )

        return video_files

    def browse_directory(
        self, path: str = "", page: int = 1, page_size: int = 20
    ) -> tuple[str, str | None, list[DirectoryEntry], int]:
        """
        Browse a directory and list its contents.

        Args:
            path: Path to browse. Empty string returns root/drives.
            page: Page number (1-based).
            page_size: Number of items per page.

        Returns:
            Tuple of (current_path, parent_path, entries, total).

        Raises:
            FolderNotFoundError: If the path does not exist.
            InvalidFolderError: If the path is not a directory.
            PermissionDeniedError: If access is denied.
        """
        import platform
        from datetime import datetime

        # Handle empty path - return drives on Windows, root on Unix
        if not path:
            if platform.system() == "Windows":
                # List available drives
                import string
                entries = []
                for letter in string.ascii_uppercase:
                    drive = f"{letter}:\\"
                    if Path(drive).exists():
                        entries.append(DirectoryEntry(
                            name=f"{letter}:",
                            path=drive,
                            is_dir=True,
                            size=None,
                            mtime=None,
                        ))
                total = len(entries)
                # 分页
                start = (page - 1) * page_size
                end = start + page_size
                return "", None, entries[start:end], total
            else:
                path = "/"

        # 路径安全验证
        folder = _sanitize_path(path)

        if not folder.exists():
            raise FolderNotFoundError(path)

        if not folder.is_dir():
            raise InvalidFolderError(path)

        try:
            all_entries: list[DirectoryEntry] = []

            for item in sorted(folder.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    stat = item.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    size = stat.st_size if item.is_file() else None

                    all_entries.append(DirectoryEntry(
                        name=item.name,
                        path=str(item.absolute()),
                        is_dir=item.is_dir(),
                        size=size,
                        mtime=mtime,
                    ))
                except PermissionError:
                    # Skip items we can't access
                    continue

            total = len(all_entries)

            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            entries = all_entries[start:end]

            # Calculate parent path
            parent = folder.parent
            parent_path = str(parent.absolute()) if parent != folder else None

            # On Windows, if parent is the drive root, keep it
            if platform.system() == "Windows" and parent_path and len(parent_path) == 3:
                # e.g., "C:\\" - keep as is
                pass
            elif platform.system() == "Windows" and str(folder.absolute()).endswith(":\\"):
                # At drive root, parent is the drive list
                parent_path = ""

            return str(folder.absolute()), parent_path, entries, total

        except PermissionError as e:
            raise PermissionDeniedError(path) from e
