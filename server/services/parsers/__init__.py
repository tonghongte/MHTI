"""Parser plugins for filename parsing."""

from server.services.parsers.base import ParseContext, ParserPlugin
from server.services.parsers.folder_context import FolderContextPlugin
from server.services.parsers.cleaner import CleanerPlugin
from server.services.parsers.episode_standard import EpisodeStandardPlugin
from server.services.parsers.episode_japanese import EpisodeJapanesePlugin
from server.services.parsers.episode_chinese import EpisodeChinesePlugin
from server.services.parsers.series_name import SeriesNamePlugin

# 默认插件列表（按优先级排序）
DEFAULT_PLUGINS: list[type[ParserPlugin]] = [
    FolderContextPlugin,  # priority=5, 最先执行，从路径提取 TMDB ID
    CleanerPlugin,
    EpisodeStandardPlugin,
    EpisodeJapanesePlugin,
    EpisodeChinesePlugin,
    SeriesNamePlugin,
]

__all__ = [
    "ParseContext",
    "ParserPlugin",
    "FolderContextPlugin",
    "CleanerPlugin",
    "EpisodeStandardPlugin",
    "EpisodeJapanesePlugin",
    "EpisodeChinesePlugin",
    "SeriesNamePlugin",
    "DEFAULT_PLUGINS",
]
