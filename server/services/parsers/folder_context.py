"""Folder context parser - extracts metadata from parent folder names.

从上层文件夹名称提取元数据，支持以下格式：
  [2025] XXX [tmdbid-12345]/Season 1/S01E01.mkv
  XXX (2025) [tmdb-12345]/S01E01.mkv

可提取：
  - TMDB ID：[tmdbid-12345] 或 [tmdb-12345]
  - 年份：[2025] 或 (2025)
  - 剧名：从文件夹名称中去除括号内容后得到
"""

import re
from pathlib import Path

from server.services.parsers.base import ParseContext, ParserPlugin

# TMDB ID 模式：[tmdbid-12345]、[tmdb-12345]、[tmdbid:12345]
TMDB_ID_PATTERN = re.compile(r"\[tmdb(?:id)?[-:](\d+)\]", re.I)

# 年份模式：[2025] 或 (2025)
FOLDER_YEAR_PATTERN = re.compile(r"[\[\(]((?:19|20)\d{2})[\]\)]")

# Season 文件夹模式：Season 1、S01 等（用于识别和提取季号）
SEASON_FOLDER_PATTERN = re.compile(r"^[Ss]eason\s*\d+$|^[Ss]\d{1,2}$")
# 从 Season 文件夹名称中提取季号
SEASON_NUMBER_PATTERN = re.compile(r"[Ss]eason\s*(\d+)|^[Ss](\d{1,2})$")

# 用于清理文件夹名称以提取剧名的模式
_BRACKET_CLEAN_PATTERNS = [
    re.compile(r"\[tmdb(?:id)?[-:]\d+\]", re.I),   # [tmdbid-12345]
    re.compile(r"[\[\(](?:19|20)\d{2}[\]\)]"),       # [2025] / (2025)
    re.compile(r"\[[^\]]*\]"),                        # 其余 [] 内容
    re.compile(r"\([^\)]*\)"),                        # 其余 () 内容
]

# 文件夹名称中的卷/副标题标记（出现时截断，后面视为副标题）
_VOLUME_SPLIT_PATTERN = re.compile(
    r"\s+"                                  # 前面必须有空白（独立词）
    r"(下[巻卷]|上[巻卷]|前[編篇]|後[編篇]|完結[編篇]"
    r"|第[一二三四五六七八九十百千\d]+[巻話編章]"
    r"|[Vv]ol\.?\s*\d+"
    r")"
)

# 从卷标记文本中提取集号
_VOLUME_FIXED_MAP = {
    "上": 1, "前": 1,
    "下": 2, "後": 2,
}


def _episode_from_volume_marker(vol_text: str) -> int | None:
    """从卷标记文本中提取集号。

    支持：
      Vol.N / vol N  → N
      上巻/上卷/前編/前篇 → 1
      下巻/下卷/後編/後篇 → 2
      第N巻/第N話/第N編/第N章 → N（仅阿拉伯数字）
    """
    # Vol.N
    vol_num = re.search(r"[Vv]ol\.?\s*(\d+)", vol_text)
    if vol_num:
        return int(vol_num.group(1))
    # 第N巻/話/編/章（仅数字）
    dai_num = re.search(r"第(\d+)[巻話編章]", vol_text)
    if dai_num:
        return int(dai_num.group(1))
    # 上/前 → 1，下/後 → 2
    for kanji, ep in _VOLUME_FIXED_MAP.items():
        if vol_text.startswith(kanji):
            return ep
    return None


def _detect_series_folder(filepath: str) -> tuple[Path | None, int | None]:
    """从文件路径向上检测剧集根文件夹和季号。

    规则：
    - 跳过文件名本身
    - 如果父目录名称匹配 Season 模式，则提取季号，再向上一级为剧集文件夹
    - 否则父目录即为剧集文件夹，季号为 None

    Returns:
        (series_folder, season_number) 元组
    """
    path = Path(filepath)
    parent = path.parent

    if SEASON_FOLDER_PATTERN.match(parent.name):
        # 提取季号
        season_num = None
        m = SEASON_NUMBER_PATTERN.search(parent.name)
        if m:
            season_num = int(m.group(1) or m.group(2))
        # 父级是 Season 文件夹，再向上
        candidate = parent.parent
        if candidate.name:  # 确保还有上层
            # 若候选剧集文件夹本身是文件系统根目录的直接子目录，则视为顶层挂载点，跳过
            if candidate.parent == Path(candidate.anchor):
                return None, None
            return candidate, season_num
        return None, None
    else:
        # 若父目录是文件系统根目录的直接子目录（如 /media、/downloads），
        # 说明文件在顶层目录下，应使用文件名而非目录名作为剧集来源
        if parent.parent == Path(parent.anchor):
            return None, None
        return parent, None


class FolderContextPlugin(ParserPlugin):
    """从上层文件夹名称提取 TMDB ID、年份和剧名。

    解析优先级：5（在 CleanerPlugin 之前执行）
    仅当 filepath 不为空时生效。
    """

    priority = 5
    name = "folder_context"

    def should_skip(self, ctx: ParseContext) -> bool:
        return not ctx.filepath

    def parse(self, ctx: ParseContext) -> ParseContext:
        if not ctx.filepath:
            return ctx

        series_folder, season_from_path = _detect_series_folder(ctx.filepath)
        if series_folder is None:
            return ctx

        folder_name = series_folder.name

        # 0. 从 Season 文件夹提取季号（优先于文件名中的季号）
        if season_from_path is not None and ctx.season is None:
            ctx.season = season_from_path
            ctx.matched_patterns.append(f"{self.name}:season")

        # 1. 提取 TMDB ID
        tmdb_match = TMDB_ID_PATTERN.search(folder_name)
        if tmdb_match and ctx.tmdb_id is None:
            ctx.tmdb_id = int(tmdb_match.group(1))
            ctx.matched_patterns.append(f"{self.name}:tmdb_id")

        # 2. 提取年份（优先于文件名中的年份）
        if ctx.year is None:
            year_match = FOLDER_YEAR_PATTERN.search(folder_name)
            if year_match:
                year = int(year_match.group(1))
                if 1950 <= year <= 2030:
                    ctx.year = year
                    ctx.matched_patterns.append(f"{self.name}:year")

        # 3. 若文件名无法解析剧名，则从文件夹名称提取
        #    SeriesNamePlugin 从文件名提取，此处作为补充（当文件名无剧名时）
        if ctx.series_name is None:
            name = folder_name
            # 先去除括号内容
            for pattern in _BRACKET_CLEAN_PATTERNS:
                name = pattern.sub("", name)
            # 在第一个卷号/副标题标记处截断，并提取集号
            # 例如 "Rune's Pharmacy Vol.2 ..." → series="Rune's Pharmacy", episode=2
            vol_match = _VOLUME_SPLIT_PATTERN.search(name)
            if vol_match:
                if ctx.episode is None:
                    ep_from_vol = _episode_from_volume_marker(vol_match.group(1))
                    if ep_from_vol is not None:
                        ctx.episode = ep_from_vol
                        ctx.matched_patterns.append(f"{self.name}:episode")
                name = name[:vol_match.start()]
            name = re.sub(r"\s+", " ", name).strip(" -_.")

            # 提取文件夹名末尾的集号标记作为集号，支持：
            #   纯数字  "OVA ピスはめ！ 1"    → series="OVA ピスはめ！", episode=1
            #   ＃N/♯N "OVA メガネnoメガミ ＃1" → series="OVA メガネnoメガミ", episode=1
            trailing_ep_match = re.search(r"(?:\s+[＃#♯]\s*|\s+)(\d{1,3})\s*$", name)
            if trailing_ep_match:
                ep_num = int(trailing_ep_match.group(1))
                name = name[:trailing_ep_match.start()].strip(" -_.")
                if ctx.episode is None:
                    ctx.episode = ep_num
                    ctx.matched_patterns.append(f"{self.name}:episode")

            if name and len(name) >= 2:
                ctx.series_name = name
                ctx.matched_patterns.append(f"{self.name}:series_name")

        return ctx
