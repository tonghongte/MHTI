"""Filename parsing service using plugin architecture."""

from server.models.parser import ParsedInfo
from server.services.parsers import DEFAULT_PLUGINS, ParseContext, ParserPlugin


class ParserService:
    """Service for parsing episode information from filenames."""

    def __init__(self, plugins: list[type[ParserPlugin]] | None = None):
        """
        初始化解析服务。

        Args:
            plugins: 插件类列表，默认使用 DEFAULT_PLUGINS
        """
        plugin_classes = plugins or DEFAULT_PLUGINS
        # 实例化插件并按优先级排序
        self._plugins = sorted(
            [cls() for cls in plugin_classes],
            key=lambda p: p.priority,
        )

    def parse(self, filename: str, filepath: str | None = None) -> ParsedInfo:
        """
        Parse episode information from a filename.

        Args:
            filename: The filename to parse.
            filepath: Optional full path for additional context.

        Returns:
            ParsedInfo with extracted information.
        """
        # 创建解析上下文
        ctx = ParseContext(
            original_filename=filename,
            filepath=filepath,
        )

        # 依次执行插件
        for plugin in self._plugins:
            if not plugin.should_skip(ctx):
                ctx = plugin.parse(ctx)

        # 转换为 ParsedInfo
        return ParsedInfo(
            original_filename=filename,
            series_name=ctx.series_name,
            season=ctx.season,
            episode=ctx.episode,
            year=ctx.year,
            tmdb_id=ctx.tmdb_id,
            is_parsed=ctx.episode is not None or ctx.series_name is not None,
            confidence=ctx.confidence,
            matched_patterns=ctx.matched_patterns,
        )

    def parse_batch(
        self, files: list[tuple[str, str | None]]
    ) -> tuple[list[ParsedInfo], float]:
        """
        Parse multiple filenames.

        Args:
            files: List of (filename, filepath) tuples.

        Returns:
            Tuple of (results list, success rate).
        """
        results = [self.parse(filename, filepath) for filename, filepath in files]
        success_count = sum(1 for r in results if r.is_parsed)
        success_rate = success_count / len(results) if results else 0.0
        return results, success_rate
