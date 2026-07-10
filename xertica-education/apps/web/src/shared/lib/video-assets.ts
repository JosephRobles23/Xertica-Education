import { api } from '@/shared/lib/api'

export type RenderedVideoAsset = {
  storage_path?: string | null
  video_url?: string | null
}

export const renderedVideoUrlFromAsset = (asset?: RenderedVideoAsset | null) =>
  asset?.storage_path || asset?.video_url || ''

export const primaryVideoPreviewMode = ({
  renderedVideoUrl,
  hasYoutubeRecommendation,
}: {
  renderedVideoUrl?: string
  hasYoutubeRecommendation: boolean
}): 'ai' | 'youtube' => {
  if (renderedVideoUrl) return 'ai'
  return hasYoutubeRecommendation ? 'youtube' : 'ai'
}

export const fetchRenderedVideoAssetUrl = async (routeId: string, moduleId: string) => {
  const params = new URLSearchParams({
    route_id: routeId,
    module_id: moduleId,
    component_kind: 'video',
  })

  const asset = await api.request<RenderedVideoAsset>(`/videos/assets?${params.toString()}`)
  return renderedVideoUrlFromAsset(asset)
}
