"""Base classes for parser plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParseContext:
    """解析上下文，在插件间传递数据。"""

    original_filename: str
    filepath: str | None = None

    # 清洗后的文件名（供后续插件使用）
    cleaned_filename: str = ""

    # 解析结果
    series_name: str | None = None
    season: int | None = None
    episode: int | None = None
    year: int | None = None
    tmdb_id: int | None = None  # 从路径中提取的 TMDB ID

    # 元数据
    confidence: float = 0.0
    matched_patterns: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.cleaned_filename:
            self.cleaned_filename = self.original_filename


class ParserPlugin(ABC):
    """解析器插件基类。"""

    # 优先级，数字越小越先执行
    priority: int = 100
    # 插件名称
    name: str = "base"

    @abstractmethod
    def parse(self, ctx: ParseContext) -> ParseContext:
        """
        解析并更新上下文。

        Args:
            ctx: 解析上下文

        Returns:
            更新后的上下文
        """
        pass

    def should_skip(self, ctx: ParseContext) -> bool:
        """
        判断是否跳过此插件。

        子类可重写此方法实现条件跳过。
        """
        return False
