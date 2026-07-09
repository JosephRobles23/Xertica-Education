'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  CircleCheck,
  ExternalLink,
  Film,
  FlaskConical,
  Link2,
  Loader2,
  Search,
  Sparkles,
  SquarePen,
  Upload as UploadIcon,
  Wand2,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Separator } from '@/shared/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Eyebrow, PageTitle } from '@/shared/components/PageHeader'
import { StatusBadge } from '@/shared/content/StatusBadge'
import { ContentPreview } from '@/shared/content/ContentPreview'
import { SourceVideoPreview } from '@/shared/content/SourceVideoPreview'
import { RefinePopover } from '@/modules/routes/components/RefinePopover'
import { api } from '@/shared/lib/api'
import {
  KIND_LABEL,
  type LearningRoute,
  type ModuleContentRef,
  type RouteModule,
  type Source,
} from '@/shared/lib/types'
import { useStore } from '@/shared/store'
import { cn } from '@/shared/lib/utils'

const sourceText = (source: Source) =>
  [source.title, source.toolName, source.vendor, source.quote].filter(Boolean).join(' ').toLowerCase()

const isYoutubeSource = (source: Source) =>
  source.kind === 'youtube' || source.plat.toLowerCase() === 'youtube' || Boolean(source.videoPreview?.youtubeId)

const isDocumentationSource = (source: Source) =>
  source.kind === 'documentation' || source.kind === 'article' || (!isYoutubeSource(source) && Boolean(source.url))

const hasSpecificYoutubeVideo = (source: Source) =>
  Boolean(source.videoPreview?.youtubeId) || Boolean(source.url?.includes('youtube.com/watch'))

const youtubeVideoIdOf = (source: Source) => {
  if (source.videoPreview?.youtubeId) return source.videoPreview.youtubeId
  const match = source.url?.match(/[?&]v=([^&]+)/)
  return match?.[1]
}

const moduleText = (module: RouteModule, content?: ModuleContentRef) =>
  [module.name, module.type, content?.summary].filter(Boolean).join(' ').toLowerCase()

function recommendedYoutubeCandidates(route: LearningRoute, module: RouteModule, content?: ModuleContentRef) {
  const targetText = moduleText(module, content)
  return route.sources
    .filter(
      (source) =>
        isYoutubeSource(source) &&
        source.verified &&
        hasSpecificYoutubeVideo(source),
    )
    .map((source) => {
      const text = sourceText(source)
      const relevance = source.relevanceScore ?? 0
      const contextualMatch =
        targetText && [source.toolName, source.vendor, source.title].some((value) =>
          value ? targetText.includes(value.toLowerCase()) || text.includes(targetText) : false,
        )

      return {
        source,
        score:
          relevance +
          (source.suggestedUse === 'video' ? 45 : 0) +
          (source.videoPreview?.youtubeId ? 100 : 0) +
          (source.verified ? 35 : 0) +
          (contextualMatch ? 20 : 0),
      }
    })
    .sort((a, b) => b.score - a.score)
    .map((candidate) => candidate.source)
}

function pickRecommendedYoutubeSource(
  route: LearningRoute,
  module: RouteModule,
  content?: ModuleContentRef,
  usedYoutubeIds: Set<string> = new Set(),
) {
  return recommendedYoutubeCandidates(route, module, content).find((source) => {
    const youtubeId = youtubeVideoIdOf(source)
    return !youtubeId || !usedYoutubeIds.has(youtubeId)
  })
}

function findRecommendedYoutubeSource(route: LearningRoute, module: RouteModule, content?: ModuleContentRef) {
  const usedYoutubeIds = new Set<string>()

  for (const routeModule of route.modules) {
    for (const routeContent of routeModule.contents) {
      if (routeModule.id === module.id && routeContent.kind === content?.kind) {
        return pickRecommendedYoutubeSource(route, module, content, usedYoutubeIds)
      }

      if (routeContent.kind !== 'video') continue

      const assigned = pickRecommendedYoutubeSource(route, routeModule, routeContent, usedYoutubeIds)
      const youtubeId = assigned ? youtubeVideoIdOf(assigned) : undefined
      if (youtubeId) usedYoutubeIds.add(youtubeId)
    }
  }

  return pickRecommendedYoutubeSource(route, module, content, usedYoutubeIds)
}

function findSecondaryYoutubeSource(route: LearningRoute, module: RouteModule, content?: ModuleContentRef) {
  const targetText = moduleText(module, content)
  const candidates = route.sources
    .filter((source) => isYoutubeSource(source) && !source.verified && hasSpecificYoutubeVideo(source))
    .map((source) => {
      const text = sourceText(source)
      const relevance = source.relevanceScore ?? 0
      const contextualMatch =
        targetText && [source.toolName, source.vendor, source.title].some((value) =>
          value ? targetText.includes(value.toLowerCase()) || text.includes(targetText) : false,
        )

      return {
        source,
        score:
          relevance +
          (source.suggestedUse === 'video' ? 45 : 0) +
          (source.videoPreview ? 20 : 0) +
          (contextualMatch ? 20 : 0),
      }
    })
    .sort((a, b) => b.score - a.score)

  return candidates[0]?.source
}

function VideoRecommendationPanel({
  route,
  module,
  content,
  recommendedSource,
  secondarySource,
  onFindAnother,
  findingAnother,
  onGenerateAiVideo,
  onEditAiVideo,
  generatingAiVideo,
  aiVideoJobProgress,
  aiVideoJobStatus,
  onRelink,
  relinking,
  linkOrigin,
  storyboardVideoUrl,
}: {
  route: LearningRoute
  module: RouteModule
  content: ModuleContentRef
  recommendedSource?: Source
  secondarySource?: Source
  onFindAnother: () => void
  findingAnother: boolean
  onGenerateAiVideo: () => void
  onEditAiVideo: () => void
  generatingAiVideo: boolean
  aiVideoJobProgress?: number
  aiVideoJobStatus?: 'queued' | 'running' | 'rendering' | 'completed' | 'failed'
  onRelink: () => void
  relinking: boolean
  linkOrigin?: 'llm' | 'heuristic' | null
  storyboardVideoUrl?: string
}) {
  const [videoOpen, setVideoOpen] = useState(Boolean(recommendedSource?.videoPreview?.youtubeId))
  const [selectedMode, setSelectedMode] = useState<'youtube' | 'ai' | 'own' | null>(null)
  const [ownVideoName, setOwnVideoName] = useState<string | null>(null)
  const ownAssetName =
    ownVideoName ??
    (route.customerContext?.baseMaterialFile?.type?.toLowerCase().startsWith('video')
      ? route.customerContext.baseMaterialFile.name
      : null)

  return (
    <div className="mb-4 rounded-lg border-[1.5px] border-accent bg-primary/6 p-3.5">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[13px] font-semibold text-ink">
            {recommendedSource ? 'Video recomendado por IA' : 'Opciones de video'}
          </div>
          <p className="mt-0.5 max-w-2xl text-[12px] leading-relaxed text-muted-foreground">
            {recommendedSource
              ? 'Elige la fuente de video para este asset durante la revisión del módulo.'
              : 'No encontramos un YouTube verificado; puedes usar el video IA, buscar otro o subir el tuyo.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {linkOrigin === 'llm' && (
            <Badge variant="outline">
              <Link2 className="size-3" /> vinculado por IA
            </Badge>
          )}
          {selectedMode && (
            <Badge variant="success">
              <Check className="size-3" /> seleccionado
            </Badge>
          )}
        </div>
      </div>

      {recommendedSource?.videoPreview ? (
        <div className="mb-3 rounded-lg bg-background/80 p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="font-display text-[14px] font-medium text-ink">
              {recommendedSource.title}
            </span>
            {recommendedSource.relevanceScore !== undefined && (
              <span className="rounded-md bg-secondary px-2 py-0.5 font-mono text-[10.5px] text-muted-foreground">
                {recommendedSource.relevanceScore}% match
              </span>
            )}
          </div>
          <SourceVideoPreview
            preview={recommendedSource.videoPreview}
            open={videoOpen}
            onOpenChange={setVideoOpen}
          />
        </div>
      ) : (
        <div className="mb-3 rounded-lg bg-background/80 p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="font-display text-[14px] font-medium text-ink">Video generado con IA</span>
            <span className="rounded-md bg-secondary px-2 py-0.5 font-mono text-[10.5px] text-muted-foreground">Veo 3</span>
          </div>
          <ContentPreview kind="video" pack={route.pack} videoUrl={storyboardVideoUrl} />
          <div className="mt-3 rounded-lg border-[1.5px] border-dashed border-input px-3 py-2 text-[12.5px] text-muted-foreground">
            {secondarySource ? (
              <div className="flex flex-wrap items-center gap-2">
                <span>
                  Candidato de YouTube sin verificación final: <span className="font-medium text-ink">{secondarySource.title}</span>
                </span>
                {secondarySource.url && (
                  <Button asChild variant="ghost" size="sm" className="h-7 px-0 text-primary">
                    <a href={secondarySource.url} target="_blank" rel="noreferrer">
                      Abrir candidato <ExternalLink className="size-3.5" />
                    </a>
                  </Button>
                )}
              </div>
            ) : (
              <span>No hay un video específico de YouTube todavía. Usa “Buscar otro” para correr Deep Research sobre este módulo.</span>
            )}
          </div>
        </div>
      )}

      {ownAssetName && selectedMode === 'own' && (
        <div className="mb-3 rounded-lg bg-background/80 px-3 py-2 text-[12.5px] text-foreground">
          Video propio seleccionado: <span className="font-medium text-ink">{ownAssetName}</span>
        </div>
      )}

      {(generatingAiVideo || aiVideoJobStatus === 'completed' || aiVideoJobStatus === 'failed') && (
        <div className="mb-3 rounded-lg border border-primary/20 bg-background/80 px-3 py-2.5 text-[12.5px]">
          {generatingAiVideo && (
            <div className="flex items-center gap-2 text-foreground">
              <Loader2 className="size-4 animate-spin text-primary" />
              <span>
                Generando video para <span className="font-medium text-ink">{module.name}</span> en segundo plano.
                Puedes seguir trabajando en quizzes, infografías o laboratorios.
                {typeof aiVideoJobProgress === 'number' ? ` Progreso: ${aiVideoJobProgress}%.` : ''}
              </span>
            </div>
          )}
          {!generatingAiVideo && aiVideoJobStatus === 'completed' && (
            <div className="flex items-center gap-2 text-foreground">
              <CheckCircle2 className="size-4 text-success" />
              <span>El video ya quedó generado. Puedes revisarlo aquí o regenerarlo si cambió el módulo.</span>
            </div>
          )}
          {!generatingAiVideo && aiVideoJobStatus === 'failed' && (
            <div className="flex items-center gap-2 text-foreground">
              <Film className="size-4 text-destructive" />
              <span>El último render falló. Puedes reintentar desde “Generar AI video” o abrir el storyboard para ajustarlo.</span>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant={selectedMode === 'youtube' ? 'success' : 'outline-primary'}
          disabled={!recommendedSource?.videoPreview}
          onClick={() => {
            setSelectedMode('youtube')
            toast.success('Video de YouTube seleccionado', {
              description: recommendedSource?.title ?? content.summary,
            })
          }}
        >
          <Check /> Usar YouTube verificado
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={relinking}
          onClick={onRelink}
        >
          {relinking ? <Loader2 className="animate-spin" /> : <Link2 />}
          Re-vincular con IA
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={findingAnother}
          onClick={onFindAnother}
        >
          {findingAnother ? <Loader2 className="animate-spin" /> : <Search />}
          Buscar otro
        </Button>
        <Button
          type="button"
          size="sm"
          variant={storyboardVideoUrl ? 'default' : 'outline'}
          disabled={generatingAiVideo}
          onClick={() => {
            setSelectedMode('ai')
            onGenerateAiVideo()
          }}
        >
          {generatingAiVideo ? <Loader2 className="animate-spin" /> : <Wand2 />}
          {storyboardVideoUrl ? 'Regenerar AI video' : 'Generar AI video'}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => {
            setSelectedMode('ai')
            onEditAiVideo()
          }}
        >
          <SquarePen /> Editar storyboard
        </Button>
        <label className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md border-[1.5px] border-input bg-card px-3 text-[12px] font-medium transition-colors hover:border-primary">
          <UploadIcon /> Video propio
          <input
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (!file) return
              setOwnVideoName(file.name)
              setSelectedMode('own')
              toast.success('Video propio seleccionado', { description: file.name })
            }}
          />
        </label>
      </div>
    </div>
  )
}

function SourceApprovalPanel({
  route,
  module,
}: {
  route: LearningRoute
  module: RouteModule
}) {
  const { replaceRouteSources } = useStore()
  const [reviewedUrls, setReviewedUrls] = useState<Set<string>>(new Set())
  const [busyUrl, setBusyUrl] = useState<string | null>(null)
  const verifiedCount = route.sources.filter(
    (source) => isDocumentationSource(source) && source.verified,
  ).length
  const suggestions = route.sources.filter(
    (source) =>
      isDocumentationSource(source) &&
      !source.verified &&
      source.status !== 'rejected' &&
      Boolean(source.url) &&
      !reviewedUrls.has(source.url ?? ''),
  )

  if (!suggestions.length) return null

  const reviewSource = async (source: Source, action: 'approve' | 'reject') => {
    if (!source.url) return
    setBusyUrl(source.url)
    try {
      await api.request(`/learning-paths/${route.id}/research-sources/review`, {
        method: 'POST',
        body: JSON.stringify({ url: source.url, action, moduleId: module.id }),
      })
      setReviewedUrls((current) => new Set(current).add(source.url!))
      toast.success(action === 'approve' ? 'Fuente aprobada' : 'Fuente rechazada', {
        description:
          action === 'approve'
            ? 'Ya está disponible para el agente de generación.'
            : 'Esta fuente no se utilizará para generar contenido.',
      })
    } catch (err) {
      toast.error('No se pudo actualizar la fuente', {
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    } finally {
      setBusyUrl(null)
    }
  }

  const replaceSource = async (source: Source) => {
    if (!source.url) return
    setBusyUrl(source.url)
    const toastId = toast.loading('Buscando otra fuente...', {
      description: `Deep Research está buscando documentación para ${module.name}.`,
    })
    try {
      const research = await api.request<{ sources: readonly Source[] }>(
        `/learning-paths/${route.id}/deep-research`,
        {
          method: 'POST',
          body: JSON.stringify({
            brief: `${route.objective}\n${module.name}`,
            moduleId: module.id,
            replaceSourceUrl: source.url,
            customerContext: route.customerContext ?? {},
          }),
        },
      )
      replaceRouteSources(route.id, research.sources)
      toast.success('Nuevas fuentes listas', { id: toastId })
    } catch (err) {
      toast.error('No se pudo buscar otra fuente', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    } finally {
      setBusyUrl(null)
    }
  }

  return (
    <div className="rounded-xl border-[1.5px] border-accent bg-primary/6 p-4">
      <div className="mb-3">
        <div className="text-[13px] font-semibold text-ink">Suggested Sources</div>
        <p className="mt-0.5 max-w-2xl text-[12px] leading-relaxed text-muted-foreground">
          La documentación verificada se guarda como URLs aprobadas para el agente de generación.
          Estas fuentes no verificadas no se usarán hasta que las apruebes.
        </p>
        {verifiedCount > 0 && (
          <Badge variant="success" className="mt-2">
            <Check className="size-3" /> {verifiedCount} verificadas automáticamente
          </Badge>
        )}
      </div>

      <div className="grid gap-2">
        {suggestions.slice(0, 4).map((source) => (
          <div
            key={source.url}
            className="flex flex-wrap items-start justify-between gap-2 rounded-lg bg-background/80 px-3 py-2.5"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12.5px] font-medium text-ink">{source.title}</div>
              <div className="mt-0.5 text-[11.5px] text-muted-foreground">
                {source.plat}
                {source.toolName ? ` · ${source.toolName}` : ''}
                {source.relevanceScore !== undefined ? ` · ${source.relevanceScore}% match` : ''}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              {source.url && (
                <Button asChild variant="ghost" size="sm" className="h-7 px-2 text-primary">
                  <a href={source.url} target="_blank" rel="noreferrer">
                    Abrir <ExternalLink className="size-3.5" />
                  </a>
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={busyUrl === source.url}
                onClick={() => reviewSource(source, 'approve')}
              >
                <Check /> Aprobar
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={busyUrl === source.url}
                onClick={() => reviewSource(source, 'reject')}
              >
                Rechazar
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled={busyUrl === source.url}
                onClick={() => replaceSource(source)}
              >
                <Search /> Buscar otra
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Panel de asset (tab visible) ──────────────────────────────── */
function ContentReviewPanel({
  route,
  module,
  content,
}: {
  route: LearningRoute
  module: RouteModule
  content: ModuleContentRef
}) {
  const router = useRouter()
  const {
    contentStatusOf,
    approveContent,
    refineContent,
    isLabGuideApproved,
    storyboardVideoUrlOf,
    setStoryboardVideoUrl,
    storyboardJobIdOf,
    setStoryboardJobId,
    clearStoryboardJobId,
    activeJobs,
    trackJob,
    replaceRouteSources,
  } = useStore()
  const [findingAnotherVideo, setFindingAnotherVideo] = useState(false)
  const [relinking, setRelinking] = useState(false)
  const [backendVideoUrl, setBackendVideoUrl] = useState('')
  // Vinculación Source↔Módulo persistida (ADR-0012): si existe, prevalece sobre la heurística.
  const [linkedUrl, setLinkedUrl] = useState<string | null>(null)
  const [linkOrigin, setLinkOrigin] = useState<'llm' | 'heuristic' | null>(null)

  const status = contentStatusOf(route.id, module.id, content.kind, content.status)
  const label = KIND_LABEL[content.kind]
  const isVideo = content.kind === 'video'
  const isLab = content.kind === 'lab'
  const labGuideOk = isLabGuideApproved(route.id)
  const labNeedsReview = isLab && status !== 'aprobado' && !labGuideOk
  const storyboardVideoUrl = isVideo ? storyboardVideoUrlOf(route.id) : ''
  const storyboardJobId = isVideo ? storyboardJobIdOf(route.id) : undefined
  const resolvedStoryboardVideoUrl = backendVideoUrl || storyboardVideoUrl
  const activeStoryboardJob = storyboardJobId ? activeJobs[storyboardJobId] : undefined
  const generatingAiVideo = isVideo && Boolean(
    activeStoryboardJob && activeStoryboardJob.status !== 'completed' && activeStoryboardJob.status !== 'failed',
  )

  // Carga la vinculación persistida de este módulo (si la hay).
  useEffect(() => {
    if (!isVideo) return
    let active = true
    api
      .request<{ links: { module_id: string; url: string | null; origin: string }[] }>(
        `/learning-paths/${route.id}/source-links`,
      )
      .then((res) => {
        if (!active) return
        const link = res.links.find((l) => l.module_id === module.id)
        if (link?.url) {
          setLinkedUrl(link.url)
          setLinkOrigin(link.origin === 'heuristic' ? 'heuristic' : 'llm')
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [isVideo, route.id, module.id])

  useEffect(() => {
    if (!isVideo) return
    let active = true
    const params = new URLSearchParams({
      route_id: route.id,
      module_id: module.id,
      component_kind: 'video',
    })
    api.request<{ storage_path?: string | null; video_url?: string | null }>(`/videos/assets?${params.toString()}`)
      .then((asset) => {
        if (!active) return
        const finalUrl = asset.storage_path || asset.video_url || ''
        if (!finalUrl) return
        setBackendVideoUrl(finalUrl)
        setStoryboardVideoUrl(route.id, finalUrl)
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [isVideo, route.id, module.id, setStoryboardVideoUrl])

  useEffect(() => {
    if (!isVideo || !storyboardJobId) return
    if (activeStoryboardJob) return
    void trackJob(storyboardJobId).catch(() => {})
  }, [isVideo, storyboardJobId, activeStoryboardJob, trackJob])

  useEffect(() => {
    if (!isVideo || !storyboardJobId || !activeStoryboardJob) return
    if (activeStoryboardJob.status === 'completed') {
      const finalUrl = activeStoryboardJob.result?.video_url || activeStoryboardJob.result?.videoUrl || ''
      if (finalUrl) {
        setBackendVideoUrl(finalUrl)
        setStoryboardVideoUrl(route.id, finalUrl)
      }
      clearStoryboardJobId(route.id)
      toast.success('Video AI generado', {
        id: `video-job-${route.id}-${module.id}`,
        description: `${module.name} quedó renderizado en segundo plano.`,
      })
      return
    }

    if (activeStoryboardJob.status === 'failed') {
      clearStoryboardJobId(route.id)
      toast.error('Falló la generación del video AI', {
        id: `video-job-${route.id}-${module.id}`,
        description: activeStoryboardJob.error || `${module.name} necesita una nueva corrida o ajustes en storyboard.`,
      })
    }
  }, [
    isVideo,
    storyboardJobId,
    activeStoryboardJob,
    route.id,
    module.id,
    module.name,
    setStoryboardVideoUrl,
    clearStoryboardJobId,
  ])

  const heuristicVideo = isVideo ? findRecommendedYoutubeSource(route, module, content) : undefined
  const linkedVideo =
    isVideo && linkedUrl ? route.sources.find((s) => s.url === linkedUrl) : undefined
  const recommendedVideo = linkedVideo ?? heuristicVideo
  const secondaryYoutubeVideo =
    isVideo && !recommendedVideo ? findSecondaryYoutubeSource(route, module, content) : undefined

  const findAnotherYoutubeVideo = async () => {
    setFindingAnotherVideo(true)
    const toastId = toast.loading('Buscando otro video de YouTube...', {
      description: 'Reutilizando Deep Research con el contexto del módulo.',
    })

    try {
      const research = await api.request<{
        detected_tools: readonly { tool: string; vendor: string }[]
        sources: readonly Source[]
      }>(`/learning-paths/${route.id}/deep-research`, {
        method: 'POST',
        body: JSON.stringify({
          brief: `${route.objective}\n${module.name}\n${content.summary}`,
          customerContext: route.customerContext ?? {},
        }),
      })

      replaceRouteSources(route.id, research.sources)
      const toolNames = research.detected_tools.map((tool) => tool.tool).join(', ')
      toast.success('Nueva recomendación lista', {
        id: toastId,
        description: toolNames ? `Deep Research actualizó opciones para ${toolNames}.` : undefined,
      })
    } catch (err) {
      console.error(err)
      toast.error('No se pudo buscar otro video', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    } finally {
      setFindingAnotherVideo(false)
    }
  }

  const relinkWithAI = async () => {
    setRelinking(true)
    const toastId = toast.loading('Vinculando el mejor video con IA…', {
      description: 'Re-rankeando las fuentes ya recolectadas para este módulo.',
    })
    try {
      const res = await api.request<{
        links: { module_id: string; url: string | null; origin: string; why?: string | null }[]
      }>(`/learning-paths/${route.id}/link-sources`, {
        method: 'POST',
        body: JSON.stringify({ module_id: module.id }),
      })
      const link = res.links.find((l) => l.module_id === module.id)
      if (link?.url) {
        setLinkedUrl(link.url)
        setLinkOrigin(link.origin === 'heuristic' ? 'heuristic' : 'llm')
        toast.success('Video re-vinculado', { id: toastId, description: link.why ?? undefined })
      } else {
        toast.info('No hay una fuente para vincular todavía', {
          id: toastId,
          description: 'Usa “Buscar otro” para traer candidatos con Deep Research.',
        })
      }
    } catch (err) {
      console.error(err)
      toast.error('No se pudo re-vincular', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    } finally {
      setRelinking(false)
    }
  }

  const generateAiVideo = async () => {
    const toastId = `video-job-${route.id}-${module.id}`
    toast.loading('Iniciando video AI...', {
      id: toastId,
      description: `El render de ${module.name} seguirá en segundo plano mientras avanzas en otros assets.`,
    })

    try {
      const res = await api.request<{ job_id: string }>('/videos/generate', {
        method: 'POST',
        body: JSON.stringify({
          route_id: route.id,
          module_id: module.id,
          component_kind: 'video',
          component_id: null,
          use_mock: false,
        }),
      })

      setStoryboardJobId(route.id, res.job_id)
      void trackJob(res.job_id).catch(() => {})

      toast.success('Video AI en cola', {
        id: toastId,
        description: 'Puedes abrir el storyboard para afinarlo o seguir trabajando en otros contenidos.',
      })
    } catch (err) {
      toast.error('No se pudo iniciar el video AI', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    }
  }

  const approveButton = (
    <Button
      variant={status === 'aprobado' ? 'outline' : 'success'}
      size="sm"
      disabled={status === 'aprobado'}
      onClick={() => {
        approveContent(route.id, module.id, content.kind)
        toast.success(`${label} aprobado`, { description: `${module.name} · ${route.name}` })
      }}
    >
      {status === 'aprobado' ? (
        <>
          <CircleCheck /> Aprobado
        </>
      ) : (
        <>
          <Check /> Aprobar
        </>
      )}
    </Button>
  )

  return (
    <div className="rounded-xl border-[1.5px] border-secondary bg-background/70 p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="font-display text-lg font-medium text-ink">{label}</span>
            <StatusBadge status={status} />
          </div>
          <p className="max-w-2xl text-[13px] leading-relaxed text-muted-foreground">
            {content.summary}
          </p>
        </div>
        <div className="flex gap-2.5">
          {approveButton}
          <RefinePopover
            label={label}
            onRefine={() => refineContent(route.id, module.id, content.kind)}
          >
            <Button variant="outline-primary" size="sm">
              <Sparkles /> Refinar
            </Button>
          </RefinePopover>
        </div>
      </div>

      {isVideo && (
        <VideoRecommendationPanel
          route={route}
          module={module}
          content={content}
          recommendedSource={recommendedVideo}
          secondarySource={secondaryYoutubeVideo}
          findingAnother={findingAnotherVideo}
          storyboardVideoUrl={resolvedStoryboardVideoUrl}
          onFindAnother={findAnotherYoutubeVideo}
          onRelink={relinkWithAI}
          relinking={relinking}
          linkOrigin={linkOrigin}
          generatingAiVideo={generatingAiVideo}
          aiVideoJobProgress={activeStoryboardJob?.progress}
          aiVideoJobStatus={activeStoryboardJob?.status}
          onGenerateAiVideo={generateAiVideo}
          onEditAiVideo={() => router.push(`/ruta/${route.id}/video-storyboard?module_id=${module.id}`)}
        />
      )}

      {labNeedsReview && (
        <button
          type="button"
          onClick={() => router.push(`/ruta/${route.id}/lab-guia`)}
          className="mb-4 flex w-full cursor-pointer items-center gap-3 rounded-lg border-[1.5px] border-accent bg-primary/8 px-3.5 py-3 text-left transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
        >
          <FlaskConical className="size-4.5 text-primary" />
          <span className="flex-1">
            <span className="block text-[13px] font-semibold text-ink">
              Personalizar guía del laboratorio
            </span>
            <span className="mt-0.5 block text-[11.5px] text-muted-foreground">
              Recomendado para ajustar la práctica. También puedes aprobar el laboratorio directamente.
            </span>
          </span>
          <ArrowRight className="size-4 text-primary" />
        </button>
      )}

      {isLab && labGuideOk && status !== 'aprobado' && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-success/10 px-3.5 py-2.5 text-[12.5px] text-foreground">
          <CircleCheck className="size-4 text-success" />
          Guía del laboratorio aprobada — el laboratorio está listo para tu aprobación.
        </div>
      )}

      {!isVideo && (
        <div className="mb-4">
          <ContentPreview kind={content.kind} pack={route.pack} />
        </div>
      )}
    </div>
  )
}

/* ── Página ────────────────────────────────────────────────────── */
export default function Ruta() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const {
    routes,
    markGenerated,
    contentStatusOf,
    moduleStatusOf,
    approveModule,
    routeProgressOf,
  } = useStore()
  const routeIndex = useMemo(() => routes.findIndex((r) => r.id === id), [routes, id])
  const route = routeIndex >= 0 ? routes[routeIndex] : undefined
  const routeOrderNo = routeIndex >= 0 ? String(routeIndex + 1).padStart(2, '0') : '—'
  const [selectedModuleIndex, setSelectedModuleIndex] = useState(0)
  const [selectedContentKind, setSelectedContentKind] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  const progress = useMemo(
    () => (route ? routeProgressOf(route) : { done: 0, total: 0, pct: 0 }),
    [route, routeProgressOf],
  )

  if (!route) {
    return (
      <div className="mx-auto max-w-md pt-16 text-center">
        <PageTitle>Ruta no encontrada</PageTitle>
        <Button asChild className="mt-6">
          <Link href="/">Volver a las rutas</Link>
        </Button>
      </div>
    )
  }

  const selectedModule = route.modules[selectedModuleIndex] ?? route.modules[0]
  const selectedModuleStatus = selectedModule ? moduleStatusOf(route.id, selectedModule) : 'borrador'
  const selectedModuleContents = selectedModule?.contents ?? []
  const selectedContent =
    selectedModuleContents.find((content) => content.kind === selectedContentKind) ?? selectedModuleContents[0]
  const selectedTab = selectedContent?.kind ?? ''
  const approvedAssets = selectedModule
    ? selectedModuleContents.filter(
        (content) => contentStatusOf(route.id, selectedModule.id, content.kind, content.status) === 'aprobado',
      ).length
    : 0
  const allAssetsApproved =
    selectedModuleContents.length > 0 && approvedAssets === selectedModuleContents.length
  const isFirstModule = selectedModuleIndex === 0
  const isLastModule = selectedModuleIndex >= route.modules.length - 1

  const goToModule = (nextIndex: number) => {
    const boundedIndex = Math.min(Math.max(nextIndex, 0), route.modules.length - 1)
    const nextModule = route.modules[boundedIndex]
    setSelectedModuleIndex(boundedIndex)
    setSelectedContentKind(nextModule?.contents[0]?.kind ?? null)
  }

  const generate = () => {
    setGenerating(true)
    toast.loading('Generando el material de todos los módulos…', { id: 'gen' })
    window.setTimeout(() => {
      markGenerated(route.id)
      toast.success('Contenido generado', {
        id: 'gen',
        description: 'Revisa el asset final antes de publicar.',
      })
      router.push(`/ruta/${route.id}/asset-final`)
    }, 1400)
  }

  const generateButton = (
    <Button disabled={generating} onClick={generate}>
      {generating ? (
        <>
          <Loader2 className="animate-spin" /> Preparando…
        </>
      ) : (
        <>
          <Wand2 /> Preparar asset final
        </>
      )}
    </Button>
  )

  return (
    <div className="mx-auto grid max-w-[1120px] items-start gap-9 lg:grid-cols-[1fr_300px]">
      <div>
        <Eyebrow>
          Ruta {routeOrderNo} · {route.name}
        </Eyebrow>
        <PageTitle className="mb-5 text-[31px]">{route.name}</PageTitle>

        {/* Objetivo */}
        <Card className="mb-7 gap-2 border-l-[3px] border-l-primary p-5">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-primary">
            TL;DR · Objetivo de la ruta
          </div>
          <p className="text-[14.5px] leading-relaxed">{route.objective}</p>
        </Card>

        {/* Módulo activo */}
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="font-display text-xl font-medium text-ink">Módulos</h2>
          <span className="font-mono text-[11px] text-muted-foreground">
            {progress.done} de {route.modules.length} aprobados
          </span>
        </div>

        {selectedModule && (
          <Card className={cn('gap-5 p-5', selectedModuleStatus === 'en-revision' && 'border-primary')}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3.5">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 font-mono text-[13px] font-semibold text-primary">
                  {selectedModule.num}
                </span>
                <span className="min-w-0">
                  <span className="block font-display text-xl font-medium leading-tight text-ink">
                    {selectedModule.name}
                  </span>
                  <span className="mt-1 block font-mono text-[10px] uppercase tracking-[0.05em] text-muted-foreground">
                    {selectedModule.type} · módulo {selectedModuleIndex + 1} de {route.modules.length}
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={selectedModuleStatus} />
                <Badge variant={allAssetsApproved ? 'success' : 'muted'}>
                  {approvedAssets}/{selectedModuleContents.length} assets
                </Badge>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-secondary px-3.5 py-3">
              <Button
                variant="outline"
                size="sm"
                disabled={isFirstModule}
                onClick={() => goToModule(selectedModuleIndex - 1)}
              >
                <ArrowLeft /> Módulo anterior
              </Button>
              <div className="flex flex-wrap justify-center gap-1.5">
                {route.modules.map((module, index) => {
                  const status = moduleStatusOf(route.id, module)
                  return (
                    <button
                      type="button"
                      key={module.id}
                      onClick={() => goToModule(index)}
                      className={cn(
                        'size-8 rounded-lg border-[1.5px] font-mono text-[11px] font-semibold transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30',
                        index === selectedModuleIndex
                          ? 'border-primary bg-primary text-primary-foreground'
                          : status === 'aprobado'
                            ? 'border-success bg-success/10 text-success'
                            : 'border-input bg-card text-muted-foreground hover:border-primary',
                      )}
                      aria-label={`Ver módulo ${module.num}`}
                    >
                      {status === 'aprobado' ? <Check className="mx-auto size-3.5" /> : module.num}
                    </button>
                  )
                })}
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={isLastModule}
                onClick={() => goToModule(selectedModuleIndex + 1)}
              >
                Siguiente módulo <ArrowRight />
              </Button>
            </div>

            {selectedModuleContents.length > 0 ? (
              <div className="grid gap-3">
                <SourceApprovalPanel route={route} module={selectedModule} />
                <Tabs value={selectedTab} onValueChange={setSelectedContentKind}>
                  <TabsList className="w-full overflow-x-auto border-b-[1.5px]">
                    {selectedModuleContents.map((content) => {
                      const status = contentStatusOf(route.id, selectedModule.id, content.kind, content.status)
                      return (
                        <TabsTrigger key={content.kind} value={content.kind} className="px-3">
                          {status === 'aprobado' && <CircleCheck className="size-3.5 text-success" />}
                          {KIND_LABEL[content.kind]}
                        </TabsTrigger>
                      )
                    })}
                  </TabsList>

                  {selectedModuleContents.map((content) => (
                    <TabsContent key={content.kind} value={content.kind} className="mt-3">
                      <ContentReviewPanel route={route} module={selectedModule} content={content} />
                    </TabsContent>
                  ))}
                </Tabs>
              </div>
            ) : (
              <div className="rounded-xl border-[1.5px] border-dashed border-input p-6 text-center text-[13px] text-muted-foreground">
                Este módulo todavía no tiene assets generados.
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-secondary px-3.5 py-3">
              <span className="text-[12.5px] leading-relaxed text-muted-foreground">
                {allAssetsApproved
                  ? 'Todos los assets de este módulo están aprobados.'
                  : 'Revisa y aprueba cada asset antes de cerrar este módulo.'}
              </span>
              {allAssetsApproved ? (
                <Button
                  variant={isLastModule ? 'success' : 'outline-primary'}
                  size="sm"
                  onClick={() => {
                    approveModule(route.id, selectedModule)
                    toast.success('Módulo aprobado', { description: `${selectedModule.name} · ${route.name}` })
                    if (!isLastModule) goToModule(selectedModuleIndex + 1)
                  }}
                >
                  {isLastModule ? (
                    <>
                      <CircleCheck /> Módulo aprobado
                    </>
                  ) : (
                    <>
                      Continuar al siguiente módulo <ArrowRight />
                    </>
                  )}
                </Button>
              ) : (
                <Badge variant="outline">
                  {approvedAssets} de {selectedModuleContents.length} aprobados
                </Badge>
              )}
            </div>
          </Card>
        )}

        {/* Asset final */}
        <Separator className="mt-6 mb-5" />
        <div className="flex items-center justify-between gap-4">
          <span className="text-[12.5px] leading-relaxed text-muted-foreground">
            Revisa los assets del módulo y prepara la versión final cuando esté lista.
          </span>
          {generateButton}
        </div>
      </div>

    </div>
  )
}
