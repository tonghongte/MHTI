"""Standard episode pattern parser (S01E01, EP01, etc.) - 标准集数解析器.

仅解析文件名，不依赖路径。
"""

import re

from server.services.parsers.base import ParseContext, ParserPlugin

# 标准集数模式（按优先级排序）
STANDARD_PATTERNS = [
    # S01E01 或 S01.E01 格式
    (r"[.\s_-]?[Ss](\d{1,2})[.\s_-]?[Ee](\d{1,3})", "season_episode"),
    # EP01 或 E01 格式（仅集数）
    (r"[.\s_-][Ee][Pp]?(\d{1,3})(?:[.\s_-]|$)", "episode_only"),
    # [01] 格式（仅集数）
    (r"\[(\d{1,3})\]", "episode_only"),
    # 末尾数字: - 01. 或 .01.（可能是品番尾号，用 trailing_number 标记以便后续判断）
    (r"[.\s_-](\d{1,3})[.\s_-]?(?:\[|$|\.(?:mp4|mkv|avi))", "trailing_number"),
]


class EpisodeStandardPlugin(ParserPlugin):
    """标准集数格式解析插件.

    解析优先级：20
    仅从文件名解析，不依赖路径。
    """

    priority = 20
    name = "episode_standard"

    def should_skip(self, ctx: ParseContext) -> bool:
        return ctx.episode is not None

    def parse(self, ctx: ParseContext) -> ParseContext:
        if self.should_skip(ctx):
            return ctx

        # 从文件名解析
        for pattern, pattern_type in STANDARD_PATTERNS:
            match = re.search(pattern, ctx.original_filename, re.I)
            if match:
                if pattern_type == "season_episode":
                    ctx.season = int(match.group(1))
                    ctx.episode = int(match.group(2))
                elif pattern_type in ("episode_only", "trailing_number"):
                    ctx.episode = int(match.group(1))

                if ctx.episode:
                    ctx.matched_patterns.append(f"{self.name}:{pattern_type}")
                    return ctx

        return ctx
