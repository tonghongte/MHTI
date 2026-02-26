# 更新日志

所有重要的项目变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增

- 🗂️ **上层文件夹刮削**：自动从父文件夹名称提取元数据
  - 支持解析 TMDB ID（`[tmdbid-12345]`、`[tmdb-12345]`、`[tmdbid:12345]`）
  - 支持解析年份（`(2025)`、`[2025]`）
  - 支持解析剧集文件夹名中的剧名（去除括号内容后提取）
  - 支持从 `Season X` / `S01` 子目录自动推断季号
  - 若从路径中获取到 TMDB ID，直接获取剧集详情，跳过 TMDB 搜索步骤
- 🔄 **原地整理模式（INPLACE）**：在当前文件夹结构内直接重命名，无需指定整理目标目录
  - 适用场景：文件夹已按剧名组织，只需规范化命名
  - 自动以现有剧集根文件夹的上级为基准进行重命名
  - 前端向导中新增「原地整理」选项，选中时隐藏目标目录字段
- 🏷️ **剧集文件夹命名包含 TMDB ID**：默认命名模板更新为 `{title} ({year}) [tmdbid-{tmdb_id}]`
  - 无论原文件夹格式为 `[2025] XXX [tmdbid-12345]` 还是 `XXX (2025)`，整理后统一命名为 `XXX (2025) [tmdbid-12345]`
  - 无 TMDB ID 或年份时自动清除空白占位符（`[tmdbid-]`、`()`）
- 🐳 **GHCR 持续部署工作流**：推送到 `main` 分支后自动构建多架构镜像并发布到 GitHub Container Registry
  - 多架构支持：`linux/amd64` + `linux/arm64`
  - 镜像标签：`main`（最新主分支）与 `sha-XXXXXXX`（按提交追踪）
  - 使用 `GITHUB_TOKEN`，无需额外配置 Secrets

### 修复

- 🔤 **字幕文件未被关联的问题**：修复 `S01E01.chs.assfonts.ass` 等多段命名字幕无法被识别的 bug
  - `_get_base_name` 现在会从右往左连续剥除语言码和描述标签（`assfonts`/`sdh`/`hi`/…），正确返回 `S01E01`
  - `_extract_language` 同步修复，即使语言码不在最后一段也能正确识别
  - `_names_match` 新增集号 fallback：若视频名与字幕 base name 均含 `SxxExx`，则以集号匹配
  - 刮削时传入 `season`/`episode` 作为最后保障，即使视频原始名称不含集号也能匹配字幕
- 📂 **孤立字幕文件无法处理**：修复影片已移走后字幕永久孤立的问题
  - 文件扫描现在也纳入含 `S01E01` 命名的字幕文件（`.ass`/`.srt`/`.ssa`/`.vtt`/`.sub`），标记 `is_subtitle: true`
  - 刮削时自动检测字幕扩展名，走专用轻量流程：读取上层文件夹 TMDB ID → 获取剧集信息 → 按命名模板计算目标路径 → 插入语言标签后移动

### 变更

- 文件整理模式新增 `inplace` 枚举值，原有 `copy`/`move`/`hardlink`/`symlink` 不受影响
- `RenameRequest` 新增 `tmdb_id` 字段，命名模板支持 `{tmdb_id}` 变量
- `ScannedFile` 新增 `is_subtitle: bool` 字段

### 计划中

- 多语言支持 (i18n)
- 批量任务队列优化
- 更多媒体源支持

---

## [1.0.0] - 2024-XX-XX

### 新增
- 🎬 视频文件名智能解析（支持标准、中文、日文格式）
- 🔍 TMDB 元数据搜索与自动匹配
- 📝 NFO 文件生成（Emby/Jellyfin 兼容）
- 📁 文件整理（复制/移动/硬链接/软链接四种模式）
- 🖼️ 海报、背景图、剧集缩略图自动下载
- 📺 字幕文件自动关联
- 👁️ 文件夹实时监控与自动刮削
- 🔗 Emby 媒体库冲突检测
- 🔐 JWT 认证与多会话管理
- 🌙 亮色/暗色主题切换
- 📊 首页统计概览
- 🐳 Docker 一键部署
- 🌐 WebSocket 实时进度推送

### 技术栈
- 后端：Python 3.11 + FastAPI + aiosqlite
- 前端：Vue 3.5 + TypeScript 5.9 + Naive UI
- 部署：Docker + Caddy

---

## 版本说明

- **[Unreleased]**: 尚未发布的变更
- **新增**: 新功能
- **变更**: 对现有功能的变更
- **弃用**: 即将移除的功能
- **移除**: 已移除的功能
- **修复**: Bug 修复
- **安全**: 安全相关修复
