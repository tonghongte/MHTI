import api from './index'
import type { TMDBSearchResponse, TMDBSeries } from './types'

const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p'

/**
 * TMDB 相关 API
 */
export const tmdbApi = {
  /**
   * 搜索剧集
   * @param fuzzy 启用模糊搜索回退（原始词无结果时自动尝试简化候选词）
   */
  async search(query: string, fuzzy = false): Promise<TMDBSearchResponse> {
    const response = await api.get<TMDBSearchResponse>('/tmdb/search', {
      params: { q: query, fuzzy },
    })
    return response.data
  },

  /**
   * 获取剧集详情
   */
  async getSeries(tmdbId: number): Promise<TMDBSeries> {
    const response = await api.get<TMDBSeries>(`/tmdb/series/${tmdbId}`)
    return response.data
  },

  /**
   * 获取图片 URL
   */
  getImageUrl(path: string | null, size: string = 'w185'): string | null {
    if (!path) return null
    return `${TMDB_IMAGE_BASE}/${size}${path}`
  },
}
