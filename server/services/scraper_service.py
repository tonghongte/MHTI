"""Scraper service for orchestrating the scraping workflow.

该模块是刮削工作流的核心编排器，通过 Mixin 模式组织代码：
- ScraperConfigMixin: 配置管理
- ScraperMetadataMixin: 元数据处理（NFO、搜索结果）
- ScraperMediaMixin: 媒体文件处理（图片、字幕、Emby）
"""

import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from server.models.emby import ConflictType
from server.models.history import LogLevel, ScrapeLogEntry, ScrapeLogStep
from server.models.organize import OrganizeMode
from server.models.rename import RenameRequest
from server.models.scraper import (
    BatchScrapeRequest,
    BatchScrapeResponse,
    ScrapeByIdRequest,
    ScrapePreview,
    ScrapeRequest,
    ScrapeResult,
    ScrapeStatus,
)
from server.services.config_service import ConfigService
from server.services.emby_service import EmbyService
from server.services.image_service import ImageService
from server.services.nfo_service import NFOService
from server.services.parser_service import ParserService
from server.services.rename_service import RenameService
from server.services.scraper_config import ScraperConfigMixin
from server.services.scraper_media import ScraperMediaMixin
from server.services.scraper_metadata import ScraperMetadataMixin
from server.services.subtitle_service import SubtitleService
from server.services.tmdb_service import TMDBService

logger = logging.getLogger(__name__)

# 日志更新回调类型
LogUpdateCallback = Callable[[list[ScrapeLogStep]], Awaitable[None]]

# 整理模式中文名称映射
_MODE_NAMES = {
    OrganizeMode.COPY: "复制",
    OrganizeMode.MOVE: "移动",
    OrganizeMode.HARDLINK: "硬链接",
    OrganizeMode.SYMLINK: "软链接",
    OrganizeMode.INPLACE: "原地整理",
}

# Season 文件夹名称匹配模式
_SEASON_FOLDER_RE = re.compile(r"^[Ss]eason\s*\d+$|^[Ss]\d{1,2}$")


def _get_mode_name(mode: OrganizeMode | None) -> str:
    """获取整理模式的中文名称。"""
    if mode is None:
        return "移动"
    return _MODE_NAMES.get(mode, "移动")


def _resolve_inplace_output_dir(file_path: str) -> str:
    """为原地整理模式计算 output_dir。

    逻辑：
    - 若文件父目录是 Season 文件夹，则向上两级作为 output_dir
    - 否则向上一级作为 output_dir

    这样 rename_service 会在 output_dir 下创建新的剧集文件夹结构，
    实现"原地"重命名效果（剧集文件夹同级改名）。
    """
    path = Path(file_path)
    parent = path.parent
    if _SEASON_FOLDER_RE.match(parent.name):
        return str(parent.parent.parent)
    return str(parent.parent)


class ScraperService(ScraperConfigMixin, ScraperMetadataMixin, ScraperMediaMixin):
    """Service for orchestrating the complete scraping workflow.

    通过 Mixin 模式组织代码，保持核心刮削逻辑清晰：
    - ScraperConfigMixin: 配置检查和获取
    - ScraperMetadataMixin: NFO 生成和搜索结果处理
    - ScraperMediaMixin: 图片下载、字幕处理、Emby 冲突检测
    """

    def __init__(
        self,
        config_service: ConfigService,
        tmdb_service: TMDBService,
        parser_service: ParserService,
        nfo_service: NFOService,
        rename_service: RenameService,
        image_service: ImageService,
        subtitle_service: SubtitleService,
        emby_service: EmbyService,
    ) -> None:
        """Initialize scraper service with explicit dependencies.

        Args:
            config_service: Configuration service instance.
            tmdb_service: TMDB API service instance.
            parser_service: Filename parser service instance.
            nfo_service: NFO generation service instance.
            rename_service: File rename/move service instance.
            image_service: Image download service instance.
            subtitle_service: Subtitle handling service instance.
            emby_service: Emby integration service instance.
        """
        self.config_service = config_service
        self.tmdb_service = tmdb_service
        self.parser_service = parser_service
        self.nfo_service = nfo_service
        self.rename_service = rename_service
        self.image_service = image_service
        self.subtitle_service = subtitle_service
        self.emby_service = emby_service

    async def preview(self, file_path: str) -> ScrapePreview:
        """Preview scrape operation without executing.

        Args:
            file_path: Path to the video file.

        Returns:
            ScrapePreview with parsed info and search results.
        """
        path = Path(file_path)

        # Parse filename (包括从上层文件夹提取元数据)
        parsed = self.parser_service.parse(path.name, file_path)

        preview = ScrapePreview(
            file_path=file_path,
            parsed_title=parsed.series_name,
            parsed_season=parsed.season,
            parsed_episode=parsed.episode,
        )

        # 若从路径中提取到 TMDB ID，直接获取剧集详情
        if parsed.tmdb_id:
            try:
                series = await self.tmdb_service.get_series_by_api(parsed.tmdb_id)
                if series:
                    from server.models.tmdb import TMDBSearchResult
                    preview.search_results = [TMDBSearchResult(
                        id=series.id,
                        name=series.name,
                        original_name=series.original_name,
                        overview=series.overview,
                        poster_path=series.poster_path,
                        first_air_date=series.first_air_date,
                        vote_average=series.vote_average,
                        adult=True,  # 仅刮削成人内容，路径已包含 TMDB ID 视为有效
                        number_of_seasons=series.number_of_seasons,
                        number_of_episodes=series.number_of_episodes,
                    )]
            except (httpx.TimeoutException, httpx.RequestError):
                pass
        # 否则通过标题搜索
        elif parsed.series_name:
            try:
                search_response = await self.tmdb_service.search_series_by_api(parsed.series_name)
                preview.search_results = search_response.results
            except (httpx.TimeoutException, httpx.RequestError):
                pass

        return preview

    async def scrape_file(
        self,
        request: ScrapeRequest,
        on_log_update: LogUpdateCallback | None = None,
    ) -> ScrapeResult:
        """Execute complete scraping workflow for a single file.

        Workflow:
        1. Parse filename to extract series name, season, episode
        2. Search TMDB using API
        3. Auto-select best match (or return candidates)
        4. Get details via API
        5. Generate NFO
        6. Move file to organized location
        7. Download images
        8. Process subtitles

        Args:
            request: Scrape request with file path and options.
            on_log_update: Optional callback for real-time log updates.

        Returns:
            ScrapeResult with operation status and details.
        """
        file_path = request.file_path
        path = Path(file_path)
        scrape_logs: list[ScrapeLogStep] = []

        async def notify_log_update():
            """通知日志更新。"""
            if on_log_update:
                await on_log_update(scrape_logs)

        # Check file exists
        if not path.exists():
            return ScrapeResult(
                file_path=file_path,
                status=ScrapeStatus.MOVE_FAILED,
                message=f"文件不存在: {file_path}",
            )

        # Step 1: Parse filename
        parse_step = ScrapeLogStep(name="解析文件名", logs=[])
        parse_step.logs.append(ScrapeLogEntry(message=f"视频文件路径: {file_path}"))
        parsed = self.parser_service.parse(path.name, file_path)

        result = ScrapeResult(
            file_path=file_path,
            status=ScrapeStatus.SUCCESS,
            parsed_title=parsed.series_name,
            parsed_season=parsed.season,
            parsed_episode=parsed.episode,
        )

        if not parsed.series_name and not parsed.tmdb_id:
            parse_step.logs.append(ScrapeLogEntry(message="无法从文件名或上层文件夹解析出剧集信息", level=LogLevel.ERROR))
            parse_step.completed = False
            scrape_logs.append(parse_step)
            await notify_log_update()
            result.status = ScrapeStatus.NO_MATCH
            result.message = "无法从文件名解析出剧集名称"
            result.scrape_logs = scrape_logs
            return result

        if parsed.tmdb_id:
            parse_step.logs.append(ScrapeLogEntry(message=f"从路径提取 TMDB ID: {parsed.tmdb_id}, 剧名: {parsed.series_name or '未知'}, S{parsed.season or '?'}E{parsed.episode or '?'}"))
        else:
            parse_step.logs.append(ScrapeLogEntry(message=f"解析结果: {parsed.series_name} S{parsed.season or '?'}E{parsed.episode or '?'}"))
        scrape_logs.append(parse_step)
        await notify_log_update()

        # Step 2: 若有 TMDB ID 则直接获取详情，否则搜索
        if parsed.tmdb_id:
            # 从路径中已获取 TMDB ID，直接跳到获取详情
            search_step = ScrapeLogStep(name="搜索 TMDB", logs=[])
            search_step.logs.append(ScrapeLogEntry(message=f"使用路径中的 TMDB ID: {parsed.tmdb_id}，跳过搜索步骤"))
            scrape_logs.append(search_step)
            await notify_log_update()
            result.selected_id = parsed.tmdb_id
        else:
            # 通过标题搜索 TMDB
            search_step = ScrapeLogStep(name="搜索 TMDB", logs=[])
            search_step.logs.append(ScrapeLogEntry(message=f"搜索关键词: {parsed.series_name}"))
            scrape_logs.append(search_step)
            await notify_log_update()

            try:
                search_response = await self.tmdb_service.search_series_by_api(parsed.series_name)
                # 只保留成人内容
                adult_results = [r for r in search_response.results if r.adult]
                result.search_results = adult_results
                search_step.logs.append(ScrapeLogEntry(message=f"找到 {len(adult_results)} 个匹配结果"))
                await notify_log_update()
            except httpx.TimeoutException:
                search_step.logs.append(ScrapeLogEntry(message="TMDB 搜索超时", level=LogLevel.ERROR))
                search_step.completed = False
                await notify_log_update()
                result.status = ScrapeStatus.SEARCH_FAILED
                result.message = "TMDB 搜索超时，请检查网络或 Cookie"
                result.scrape_logs = scrape_logs
                return result
            except httpx.RequestError as e:
                search_step.logs.append(ScrapeLogEntry(message=f"TMDB 搜索失败: {str(e)}", level=LogLevel.ERROR))
                search_step.completed = False
                await notify_log_update()
                result.status = ScrapeStatus.SEARCH_FAILED
                result.message = f"TMDB 搜索失败: {str(e)}"
                result.scrape_logs = scrape_logs
                return result

            if not adult_results:
                search_step.logs.append(ScrapeLogEntry(message="未找到匹配的成人剧集", level=LogLevel.WARNING))
                search_step.completed = False
                await notify_log_update()
                result.status = ScrapeStatus.NO_MATCH
                result.message = f"未找到匹配的成人剧集: {parsed.series_name}"
                result.scrape_logs = scrape_logs
                return result

            # Step 3: Select match
            result.search_results = adult_results

            if request.auto_select and len(adult_results) == 1:
                # 只有一个结果时自动选择
                selected = adult_results[0]
                result.selected_id = selected.id
            elif request.auto_select and len(adult_results) > 1:
                # 多个结果时需要用户选择，先获取每个结果的详情
                search_step.logs.append(ScrapeLogEntry(message="获取各剧集详情..."))
                await notify_log_update()
                enriched_results = await self._enrich_search_results(adult_results)
                result.search_results = enriched_results
                result.status = ScrapeStatus.NEED_SELECTION
                result.message = f"找到 {len(adult_results)} 个匹配结果，请手动选择"
                result.scrape_logs = scrape_logs
                return result
            else:
                # Return results for manual selection
                search_step.logs.append(ScrapeLogEntry(message="获取各剧集详情..."))
                await notify_log_update()
                enriched_results = await self._enrich_search_results(adult_results)
                result.search_results = enriched_results
                result.status = ScrapeStatus.NEED_SELECTION
                result.message = "请手动选择匹配的剧集"
                result.scrape_logs = scrape_logs
                return result

        # Step 4: Get details via API
        detail_step = ScrapeLogStep(name="获取详情", logs=[])
        detail_step.logs.append(ScrapeLogEntry(message=f"获取剧集详情: TMDB ID {result.selected_id}"))
        scrape_logs.append(detail_step)
        await notify_log_update()

        try:
            series = await self.tmdb_service.get_series_by_api(result.selected_id)
            if series is None:
                detail_step.logs.append(ScrapeLogEntry(message="无法获取剧集详情", level=LogLevel.ERROR))
                detail_step.completed = False
                await notify_log_update()
                result.status = ScrapeStatus.API_FAILED
                result.message = f"无法获取剧集详情: ID {result.selected_id}"
                result.scrape_logs = scrape_logs
                return result
            result.series_info = series
            detail_step.logs.append(ScrapeLogEntry(message=f"剧集名称: {series.name}"))
            await notify_log_update()
        except ValueError as e:
            detail_step.logs.append(ScrapeLogEntry(message=str(e), level=LogLevel.ERROR))
            detail_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.API_FAILED
            result.message = str(e)
            result.scrape_logs = scrape_logs
            return result
        except httpx.TimeoutException:
            detail_step.logs.append(ScrapeLogEntry(message="TMDB API 请求超时", level=LogLevel.ERROR))
            detail_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.API_FAILED
            result.message = "TMDB API 请求超时"
            result.scrape_logs = scrape_logs
            return result
        except httpx.RequestError as e:
            detail_step.logs.append(ScrapeLogEntry(message=f"TMDB API 请求失败: {str(e)}", level=LogLevel.ERROR))
            detail_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.API_FAILED
            result.message = f"TMDB API 请求失败: {str(e)}"
            result.scrape_logs = scrape_logs
            return result

        # Step 4.5: Check if episode is missing
        if parsed.episode is None:
            # 如果剧集只有1集，自动选择
            total_episodes = series.number_of_episodes or 0
            if total_episodes == 1:
                parsed.episode = 1
                logger.info("剧集只有1集，自动选择 E01")
            else:
                # 多集需要手动选择，先获取季详情
                result.series_info = series
                season_num = parsed.season if parsed.season is not None else 1
                try:
                    season_detail = await self.tmdb_service.get_season_by_api(
                        result.selected_id, season_num
                    )
                    # 更新 series 中对应季的 episodes 信息
                    for i, s in enumerate(series.seasons):
                        if s.season_number == season_num:
                            series.seasons[i] = season_detail
                            break
                    result.series_info = series
                except Exception as e:
                    logger.warning(f"获取季度详情失败: {e}")

                result.status = ScrapeStatus.NEED_SEASON_EPISODE
                result.message = f"剧集共 {total_episodes} 集，请手动选择"
                result.scrape_logs = scrape_logs
                return result

        # Determine season and episode
        season_num = parsed.season if parsed.season is not None else 1
        episode_num = parsed.episode if parsed.episode is not None else 1

        # 记录程序选择的季/集
        select_step = ScrapeLogStep(name="确定季/集", logs=[])
        scrape_logs.append(select_step)
        if parsed.season is not None and parsed.episode is not None:
            select_step.logs.append(ScrapeLogEntry(message=f"从文件名解析: S{season_num:02d}E{episode_num:02d}"))
        else:
            msgs = []
            if parsed.season is None:
                msgs.append("季号默认为 1")
            if parsed.episode is None:
                msgs.append("集号默认为 1")
            select_step.logs.append(ScrapeLogEntry(message=f"程序自动选择: S{season_num:02d}E{episode_num:02d} ({', '.join(msgs)})"))
        await notify_log_update()

        # Step 5: Get season details (for episode info)
        season_info = None
        try:
            season_info = await self.tmdb_service.get_season_by_api(
                result.selected_id, season_num
            )
            logger.info(f"获取季度详情: Season {season_num}, 共 {len(season_info.episodes) if season_info and season_info.episodes else 0} 集")
        except Exception as e:
            logger.warning(f"获取季度详情失败: {e}")

        # Step 5.5: Emby 冲突检查
        emby_step = ScrapeLogStep(name="Emby 冲突检查", logs=[])
        scrape_logs.append(emby_step)
        try:
            conflict_result = await self._check_emby_conflict(
                series_name=series.name,
                tmdb_id=result.selected_id,
                season=season_num,
                episode=episode_num,
            )
        except Exception as e:
            logger.warning(f"Emby 冲突检查异常: {e}")
            from server.models.emby import ConflictCheckResult
            conflict_result = ConflictCheckResult(conflict_type=ConflictType.NO_CONFLICT)

        if conflict_result.conflict_type == ConflictType.EPISODE_EXISTS:
            emby_step.logs.append(ScrapeLogEntry(
                message=conflict_result.message or "Emby 中已存在该集",
                level=LogLevel.WARNING,
            ))
            emby_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.EMBY_CONFLICT
            result.message = conflict_result.message
            result.emby_conflict = conflict_result
            result.scrape_logs = scrape_logs
            return result
        elif conflict_result.conflict_type == ConflictType.SERIES_EXISTS:
            emby_step.logs.append(ScrapeLogEntry(
                message=conflict_result.message or "Emby 中已存在该剧集",
                level=LogLevel.SUCCESS,
            ))
        else:
            emby_step.logs.append(ScrapeLogEntry(message="无冲突"))
        await notify_log_update()

        # Step 6: Generate NFO
        nfo_step = ScrapeLogStep(name="生成 NFO", logs=[])
        scrape_logs.append(nfo_step)
        try:
            nfo_content = self._generate_episode_nfo(series, season_num, episode_num, season_info)
            nfo_step.logs.append(ScrapeLogEntry(message="NFO 内容生成成功"))
            await notify_log_update()
        except Exception as e:
            nfo_step.logs.append(ScrapeLogEntry(message=f"NFO 生成失败: {str(e)}", level=LogLevel.ERROR))
            nfo_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.NFO_FAILED
            result.message = f"NFO 生成失败: {str(e)}"
            result.scrape_logs = scrape_logs
            return result

        # Step 7: Move file using RenameService
        mode_name = _get_mode_name(request.link_mode)
        move_step = ScrapeLogStep(name=f"{mode_name}文件", logs=[])
        scrape_logs.append(move_step)
        try:
            year = series.first_air_date.year if series.first_air_date else None

            # 原地整理模式：自动以当前剧集文件夹的上级为 output_dir，内部使用 MOVE
            if request.link_mode == OrganizeMode.INPLACE:
                effective_output_dir = _resolve_inplace_output_dir(file_path)
                effective_link_mode = OrganizeMode.MOVE
                move_step.logs.append(ScrapeLogEntry(message=f"原地整理：在 {effective_output_dir} 内重命名"))
            else:
                effective_output_dir = request.output_dir
                effective_link_mode = request.link_mode

            rename_request = RenameRequest(
                source_path=file_path,
                title=series.name,
                season=season_num,
                episode=episode_num,
                year=year,
                tmdb_id=result.selected_id,
                output_dir=effective_output_dir,
                link_mode=effective_link_mode,
            )

            move_step.logs.append(ScrapeLogEntry(message=f"源文件: {file_path}"))
            move_step.logs.append(ScrapeLogEntry(message=f"目标目录: {effective_output_dir or '原目录'}"))
            move_step.logs.append(ScrapeLogEntry(message=f"整理模式: {mode_name}"))
            await notify_log_update()

            rename_result = self.rename_service.execute_rename(rename_request)

            if not rename_result.success:
                # 检查是否是文件冲突
                if rename_result.error and "already exists" in rename_result.error:
                    move_step.logs.append(ScrapeLogEntry(message=f"目标文件已存在: {rename_result.dest_path}", level=LogLevel.WARNING))
                    move_step.completed = False
                    await notify_log_update()
                    result.status = ScrapeStatus.FILE_CONFLICT
                    result.message = f"目标文件已存在: {rename_result.dest_path}"
                    result.dest_path = rename_result.dest_path
                    result.scrape_logs = scrape_logs
                    return result
                move_step.logs.append(ScrapeLogEntry(message=f"{mode_name}失败: {rename_result.error}", level=LogLevel.ERROR))
                move_step.completed = False
                await notify_log_update()
                result.status = ScrapeStatus.MOVE_FAILED
                result.message = rename_result.error
                result.scrape_logs = scrape_logs
                return result

            result.dest_path = rename_result.dest_path
            move_step.logs.append(ScrapeLogEntry(message=f"文件{mode_name}成功: {rename_result.dest_path}"))
            await notify_log_update()

            # 获取剧集文件夹路径（Season 文件夹的父目录）
            dest_file = Path(rename_result.dest_path)
            season_folder = dest_file.parent
            series_folder = season_folder.parent

            # 确定元数据输出目录（NFO、图片）
            if request.metadata_dir:
                # 使用独立的元数据目录，保持相同的目录结构
                metadata_base = Path(request.metadata_dir)
                metadata_series_folder = metadata_base / series_folder.name
                metadata_season_folder = metadata_series_folder / season_folder.name
                metadata_season_folder.mkdir(parents=True, exist_ok=True)
            else:
                # 元数据与视频同目录
                metadata_series_folder = series_folder
                metadata_season_folder = season_folder

            # Write episode NFO file (if enabled)
            nfo_config = await self._get_effective_nfo_config(request.advanced_settings)
            if nfo_config["nfo_enabled"]:
                nfo_path = metadata_season_folder / f"{dest_file.stem}.nfo"
                nfo_path.write_text(nfo_content, encoding="utf-8")
                result.nfo_path = str(nfo_path)
                move_step.logs.append(ScrapeLogEntry(message=f"NFO 文件已写入: {nfo_path}"))

                # 生成 tvshow.nfo（剧集信息）到剧集文件夹
                tvshow_nfo_path = metadata_series_folder / "tvshow.nfo"
                if not tvshow_nfo_path.exists():
                    metadata_series_folder.mkdir(parents=True, exist_ok=True)
                    tvshow_nfo_data = self.nfo_service.tvshow_from_tmdb(series)
                    tvshow_nfo_content = self.nfo_service.generate_tvshow_nfo(tvshow_nfo_data)
                    tvshow_nfo_path.write_text(tvshow_nfo_content, encoding="utf-8")
                    move_step.logs.append(ScrapeLogEntry(message="tvshow.nfo 已生成"))

                # 生成 season.nfo 到季度文件夹
                season_nfo_path = metadata_season_folder / "season.nfo"
                if not season_nfo_path.exists():
                    season_nfo_data = self._get_season_nfo_data(series, season_num)
                    season_nfo_content = self.nfo_service.generate_season_nfo(season_nfo_data)
                    season_nfo_path.write_text(season_nfo_content, encoding="utf-8")
                    move_step.logs.append(ScrapeLogEntry(message="season.nfo 已生成"))
            else:
                move_step.logs.append(ScrapeLogEntry(message="NFO 生成已跳过（配置禁用）"))

            await notify_log_update()

            # Step 8: Download images (based on config)
            image_step = ScrapeLogStep(name="下载图片", logs=[])
            scrape_logs.append(image_step)
            await notify_log_update()

            download_config = await self._get_effective_download_config(request.advanced_settings)

            # 下载剧集封面和背景图到元数据剧集文件夹
            if download_config["download_poster"] or download_config["download_fanart"]:
                await self._download_series_images(
                    series,
                    str(metadata_series_folder),
                    download_poster=download_config["download_poster"],
                    download_fanart=download_config["download_fanart"],
                )
                image_step.logs.append(ScrapeLogEntry(message="剧集图片处理完成"))
            else:
                image_step.logs.append(ScrapeLogEntry(message="剧集图片下载已跳过（配置禁用）"))
            await notify_log_update()

            # 下载集封面图到元数据季度文件夹
            if download_config["download_thumb"]:
                await self._download_episode_image(
                    season_info, season_num, episode_num, str(metadata_season_folder), dest_file.stem
                )
                image_step.logs.append(ScrapeLogEntry(message="集封面图处理完成"))
            else:
                image_step.logs.append(ScrapeLogEntry(message="集封面图下载已跳过（配置禁用）"))
            await notify_log_update()

            # 处理关联字幕文件
            self._process_subtitles(file_path, str(dest_file), season=season_num, episode=episode_num)

        except Exception as e:
            move_step.logs.append(ScrapeLogEntry(message=f"文件{mode_name}失败: {str(e)}", level=LogLevel.ERROR))
            move_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.MOVE_FAILED
            result.message = f"文件{mode_name}失败: {str(e)}"
            result.scrape_logs = scrape_logs
            return result

        # 设置集信息
        if season_info and season_info.episodes:
            for ep in season_info.episodes:
                if ep.episode_number == episode_num:
                    result.episode_info = ep
                    break

        # 更新实际使用的季/集号
        result.parsed_season = season_num
        result.parsed_episode = episode_num

        result.status = ScrapeStatus.SUCCESS
        result.message = "刮削完成"
        result.scrape_logs = scrape_logs
        await notify_log_update()
        return result

    async def scrape_by_id(
        self,
        request: ScrapeByIdRequest,
        on_log_update: LogUpdateCallback | None = None,
    ) -> ScrapeResult:
        """Scrape file with manually specified TMDB ID.

        Use this when automatic search fails.

        Args:
            request: Request with file path and TMDB ID.
            on_log_update: Optional callback for real-time log updates.

        Returns:
            ScrapeResult with operation status.
        """
        file_path = request.file_path
        path = Path(file_path)
        scrape_logs: list[ScrapeLogStep] = []

        async def notify_log_update():
            """通知日志更新。"""
            if on_log_update:
                await on_log_update(scrape_logs)

        if not path.exists():
            return ScrapeResult(
                file_path=file_path,
                status=ScrapeStatus.MOVE_FAILED,
                message=f"文件不存在: {file_path}",
            )

        result = ScrapeResult(
            file_path=file_path,
            status=ScrapeStatus.SUCCESS,
            selected_id=request.tmdb_id,
            parsed_season=request.season,
            parsed_episode=request.episode,
        )

        # Step 1: 获取剧集详情
        detail_step = ScrapeLogStep(name="获取详情", logs=[])
        detail_step.logs.append(ScrapeLogEntry(message=f"TMDB ID: {request.tmdb_id}, S{request.season:02d}E{request.episode:02d}"))
        scrape_logs.append(detail_step)
        await notify_log_update()

        try:
            series = await self.tmdb_service.get_series_by_api(request.tmdb_id)
            if series is None:
                detail_step.logs.append(ScrapeLogEntry(message="无法获取剧集详情", level=LogLevel.ERROR))
                detail_step.completed = False
                await notify_log_update()
                result.status = ScrapeStatus.API_FAILED
                result.message = f"无法获取剧集详情: ID {request.tmdb_id}"
                result.scrape_logs = scrape_logs
                return result
            result.series_info = series
            detail_step.logs.append(ScrapeLogEntry(message=f"剧集名称: {series.name}"))
            await notify_log_update()
        except ValueError as e:
            detail_step.logs.append(ScrapeLogEntry(message=str(e), level=LogLevel.ERROR))
            detail_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.API_FAILED
            result.message = str(e)
            result.scrape_logs = scrape_logs
            return result
        except (httpx.TimeoutException, httpx.RequestError) as e:
            detail_step.logs.append(ScrapeLogEntry(message=f"TMDB API 请求失败: {str(e)}", level=LogLevel.ERROR))
            detail_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.API_FAILED
            result.message = f"TMDB API 请求失败: {str(e)}"
            result.scrape_logs = scrape_logs
            return result

        # Get season details (for episode info)
        season_info = None
        try:
            season_info = await self.tmdb_service.get_season_by_api(
                request.tmdb_id, request.season
            )
            detail_step.logs.append(ScrapeLogEntry(message=f"获取季度详情: 共 {len(season_info.episodes) if season_info and season_info.episodes else 0} 集"))
            await notify_log_update()
        except Exception as e:
            logger.warning(f"获取季度详情失败: {e}")

        # Step 2: 生成 NFO
        nfo_step = ScrapeLogStep(name="生成 NFO", logs=[])
        scrape_logs.append(nfo_step)
        await notify_log_update()
        try:
            nfo_content = self._generate_episode_nfo(
                series, request.season, request.episode, season_info
            )
            nfo_step.logs.append(ScrapeLogEntry(message="NFO 内容生成成功"))
            await notify_log_update()
        except Exception as e:
            nfo_step.logs.append(ScrapeLogEntry(message=f"NFO 生成失败: {str(e)}", level=LogLevel.ERROR))
            nfo_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.NFO_FAILED
            result.message = f"NFO 生成失败: {str(e)}"
            result.scrape_logs = scrape_logs
            return result

        # Step 3: 移动文件
        mode_name = _get_mode_name(request.link_mode)
        move_step = ScrapeLogStep(name=f"{mode_name}文件", logs=[])
        scrape_logs.append(move_step)
        await notify_log_update()
        try:
            year = series.first_air_date.year if series.first_air_date else None

            # 原地整理模式：自动以当前剧集文件夹的上级为 output_dir，内部使用 MOVE
            if request.link_mode == OrganizeMode.INPLACE:
                effective_output_dir = _resolve_inplace_output_dir(file_path)
                effective_link_mode = OrganizeMode.MOVE
                move_step.logs.append(ScrapeLogEntry(message=f"原地整理：在 {effective_output_dir} 内重命名"))
            else:
                effective_output_dir = request.output_dir
                effective_link_mode = request.link_mode

            rename_request = RenameRequest(
                source_path=file_path,
                title=series.name,
                season=request.season,
                episode=request.episode,
                year=year,
                tmdb_id=request.tmdb_id,
                output_dir=effective_output_dir,
                link_mode=effective_link_mode,
            )

            move_step.logs.append(ScrapeLogEntry(message=f"源文件: {path.name}"))
            move_step.logs.append(ScrapeLogEntry(message=f"目标目录: {effective_output_dir or '原目录'}"))
            move_step.logs.append(ScrapeLogEntry(message=f"整理模式: {mode_name}"))
            await notify_log_update()

            rename_result = self.rename_service.execute_rename(rename_request)

            if not rename_result.success:
                move_step.logs.append(ScrapeLogEntry(message=f"{mode_name}失败: {rename_result.error}", level=LogLevel.ERROR))
                move_step.completed = False
                await notify_log_update()
                result.status = ScrapeStatus.MOVE_FAILED
                result.message = rename_result.error
                result.scrape_logs = scrape_logs
                return result

            result.dest_path = rename_result.dest_path
            move_step.logs.append(ScrapeLogEntry(message=f"文件{mode_name}成功: {rename_result.dest_path}"))
            await notify_log_update()

            # 获取剧集文件夹路径（Season 文件夹的父目录）
            dest_file = Path(rename_result.dest_path)
            season_folder = dest_file.parent
            series_folder = season_folder.parent

            # 确定元数据输出目录（NFO、图片）
            if request.metadata_dir:
                # 使用独立的元数据目录，保持相同的目录结构
                metadata_base = Path(request.metadata_dir)
                metadata_series_folder = metadata_base / series_folder.name
                metadata_season_folder = metadata_series_folder / season_folder.name
                metadata_season_folder.mkdir(parents=True, exist_ok=True)
            else:
                # 元数据与视频同目录
                metadata_series_folder = series_folder
                metadata_season_folder = season_folder

            # Write episode NFO (if enabled)
            nfo_config = await self._get_effective_nfo_config(request.advanced_settings)
            if nfo_config["nfo_enabled"]:
                nfo_path = metadata_season_folder / f"{dest_file.stem}.nfo"
                nfo_path.write_text(nfo_content, encoding="utf-8")
                result.nfo_path = str(nfo_path)
                move_step.logs.append(ScrapeLogEntry(message=f"NFO 文件已写入: {nfo_path}"))

                # 生成 tvshow.nfo（剧集信息）到剧集文件夹
                tvshow_nfo_path = metadata_series_folder / "tvshow.nfo"
                if not tvshow_nfo_path.exists():
                    metadata_series_folder.mkdir(parents=True, exist_ok=True)
                    tvshow_nfo_data = self.nfo_service.tvshow_from_tmdb(series)
                    tvshow_nfo_content = self.nfo_service.generate_tvshow_nfo(tvshow_nfo_data)
                    tvshow_nfo_path.write_text(tvshow_nfo_content, encoding="utf-8")
                    move_step.logs.append(ScrapeLogEntry(message="tvshow.nfo 已生成"))

                # 生成 season.nfo 到季度文件夹
                season_nfo_path = metadata_season_folder / "season.nfo"
                if not season_nfo_path.exists():
                    season_nfo_data = self._get_season_nfo_data(series, request.season)
                    season_nfo_content = self.nfo_service.generate_season_nfo(season_nfo_data)
                    season_nfo_path.write_text(season_nfo_content, encoding="utf-8")
                    move_step.logs.append(ScrapeLogEntry(message="season.nfo 已生成"))
            else:
                move_step.logs.append(ScrapeLogEntry(message="NFO 生成已跳过（配置禁用）"))

            await notify_log_update()

            # Step 4: 下载图片 (based on config)
            image_step = ScrapeLogStep(name="下载图片", logs=[])
            scrape_logs.append(image_step)
            await notify_log_update()

            download_config = await self._get_effective_download_config(request.advanced_settings)

            # 下载剧集封面和背景图到元数据剧集文件夹
            if download_config["download_poster"] or download_config["download_fanart"]:
                await self._download_series_images(
                    series,
                    str(metadata_series_folder),
                    download_poster=download_config["download_poster"],
                    download_fanart=download_config["download_fanart"],
                )
                image_step.logs.append(ScrapeLogEntry(message="剧集图片处理完成"))
            else:
                image_step.logs.append(ScrapeLogEntry(message="剧集图片下载已跳过（配置禁用）"))
            await notify_log_update()

            # 下载集封面图到元数据季度文件夹
            if download_config["download_thumb"]:
                await self._download_episode_image(
                    season_info, request.season, request.episode, str(metadata_season_folder), dest_file.stem
                )
                image_step.logs.append(ScrapeLogEntry(message="集封面图处理完成"))
            else:
                image_step.logs.append(ScrapeLogEntry(message="集封面图下载已跳过（配置禁用）"))
            await notify_log_update()

            # 处理关联字幕文件
            self._process_subtitles(file_path, str(dest_file), season=request.season, episode=request.episode)

        except Exception as e:
            move_step.logs.append(ScrapeLogEntry(message=f"文件{mode_name}失败: {str(e)}", level=LogLevel.ERROR))
            move_step.completed = False
            await notify_log_update()
            result.status = ScrapeStatus.MOVE_FAILED
            result.message = f"文件{mode_name}失败: {str(e)}"
            result.scrape_logs = scrape_logs
            return result

        # 设置集信息
        if season_info and season_info.episodes:
            for ep in season_info.episodes:
                if ep.episode_number == request.episode:
                    result.episode_info = ep
                    break

        result.status = ScrapeStatus.SUCCESS
        result.message = "刮削完成"
        result.scrape_logs = scrape_logs
        await notify_log_update()
        return result

    async def batch_scrape(self, request: BatchScrapeRequest) -> BatchScrapeResponse:
        """Batch scrape multiple files.

        Args:
            request: Batch request with file paths.

        Returns:
            BatchScrapeResponse with all results.
        """
        results: list[ScrapeResult] = []

        for file_path in request.file_paths:
            if request.dry_run:
                # Preview only
                preview = await self.preview(file_path)
                results.append(
                    ScrapeResult(
                        file_path=file_path,
                        status=ScrapeStatus.SUCCESS,
                        parsed_title=preview.parsed_title,
                        parsed_season=preview.parsed_season,
                        parsed_episode=preview.parsed_episode,
                        search_results=preview.search_results,
                    )
                )
            else:
                scrape_request = ScrapeRequest(
                    file_path=file_path,
                    output_dir=request.output_dir,
                    auto_select=request.auto_select,
                )
                result = await self.scrape_file(scrape_request)
                results.append(result)

        success_count = sum(1 for r in results if r.status == ScrapeStatus.SUCCESS)
        failed_count = len(results) - success_count

        return BatchScrapeResponse(
            total=len(results),
            success=success_count,
            failed=failed_count,
            results=results,
        )
