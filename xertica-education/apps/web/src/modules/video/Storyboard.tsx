'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { ArrowRight, Check, Info, RefreshCcw, SquarePen, Film, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Progress } from '@/shared/ui/progress'
import { Textarea } from '@/shared/ui/textarea'
import { PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { getRoute } from '@/shared/data/routes'
import type { LearningRoute } from '@/shared/lib/types'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import { fetchRenderedVideoAssetUrl, type RenderedVideoAsset, renderedVideoUrlFromAsset } from '@/shared/lib/video-assets'

export type VisualType = 'text_card' | 'hero_title' | 'stat_card' | 'callout' | 'comparison' | 'bar_chart' | 'line_chart' | 'pie_chart' | 'kpi_grid' | 'progress_bar' | 'terminal_scene' | 'screenshot_scene' | 'ai_video' | 'ai_illustration'

type GroundingStatus = 'kb_grounded' | 'module_grounded'
type StoryboardSource = 'idle' | 'backend' | 'fallback_invalid_target' | 'fallback_error' | 'fallback_empty'
type RenderPhase =
  | 'queueing'
  | 'tts'
  | 'visuals'
  | 'music'
  | 'timeline'
  | 'render'
  | 'validate'
  | 'upload'
  | 'done'

type RenderPhaseMeta = {
  phase: RenderPhase
  shortLabel: string
  label: string
  start: number
  end: number
  description: string
}

export type StoryboardScene = {
  scene_number: number
  narration: string
  visual_type: VisualType
  visual_config: Record<string, unknown>
  teaching_point?: string | null
  pedagogical_intent?: string | null
  teaching_pattern?: string | null
  visual_rationale?: string | null
  grounding_status?: GroundingStatus | null
}

export type ReviewScene = {
  sceneNumber: number
  tag: string
  budget: number
  narration: string
  visualType: VisualType
  visualConfig: Record<string, unknown>
  teachingPoint: string
  pedagogicalIntent: string
  teachingPattern: string
  visualRationale: string
  groundingStatus: GroundingStatus
}

const RENDER_PHASES: RenderPhaseMeta[] = [
  { phase: 'queueing', shortLabel: 'En cola', label: 'Encolando render en la nube...', start: 0, end: 4, description: 'Preparando el job y reservando el pipeline.' },
  { phase: 'tts', shortLabel: 'Narración', label: 'Sintetizando narración por escena...', start: 5, end: 24, description: 'Generando el audio de narración para cada escena.' },
  { phase: 'visuals', shortLabel: 'Visuales', label: 'Preparando visuales y capturas...', start: 25, end: 34, description: 'Creando imágenes, videos y capturas según el storyboard.' },
  { phase: 'music', shortLabel: 'Música', label: 'Buscando música de fondo...', start: 35, end: 44, description: 'Buscando y descargando la cama musical del video.' },
  { phase: 'timeline', shortLabel: 'Timeline', label: 'Armando el plan de edición...', start: 45, end: 64, description: 'Uniendo narración, visuales y decisiones de edición.' },
  { phase: 'render', shortLabel: 'Render', label: 'Renderizando video final en Remotion...', start: 65, end: 84, description: 'Componiendo el MP4 final del video.' },
  { phase: 'validate', shortLabel: 'Validación', label: 'Validando duración y archivo final...', start: 85, end: 94, description: 'Verificando duración, tamaño y salida final.' },
  { phase: 'upload', shortLabel: 'Subida', label: 'Subiendo el MP4 final...', start: 95, end: 99, description: 'Publicando el archivo final en storage.' },
  { phase: 'done', shortLabel: 'Listo', label: '¡Generación Completada!', start: 100, end: 100, description: 'El video ya quedó generado y disponible.' },
]

const SLOW_VISUAL_TYPES: readonly VisualType[] = ['ai_video', 'ai_illustration', 'screenshot_scene']

const wordCount = (text: string) => text.trim().split(/\s+/).filter(Boolean).length
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export const isValidUuid = (value: string | undefined): value is string => Boolean(value && UUID_PATTERN.test(value))
export const hasRenderTargetModuleId = (moduleId: string | undefined): moduleId is string => Boolean(moduleId && moduleId.trim().length > 0)
export const canRenderAiStoryboard = (storyboardSource: StoryboardSource) => storyboardSource !== 'fallback_invalid_target'
export const renderActionLabel = (
  renderingState: 'idle' | 'rendering' | 'success' | 'failed',
  hasExistingRender: boolean,
) => {
  if (renderingState === 'rendering') return 'Renderizando video…'
  return hasExistingRender ? 'Regenerar Video' : 'Renderizar Video'
}

export const renderPhaseFromProgress = (progress: number): RenderPhase => {
  if (progress >= 100) return 'done'
  if (progress >= 95) return 'upload'
  if (progress >= 85) return 'validate'
  if (progress >= 65) return 'render'
  if (progress >= 45) return 'timeline'
  if (progress >= 35) return 'music'
  if (progress >= 25) return 'visuals'
  if (progress >= 5) return 'tts'
  return 'queueing'
}

export const renderPhaseLabel = (progress: number): string => {
  const phase = renderPhaseFromProgress(progress)
  return RENDER_PHASES.find((item) => item.phase === phase)?.label ?? 'Encolando render en la nube...'
}

const renderPhaseMetaForProgress = (progress: number): RenderPhaseMeta =>
  RENDER_PHASES.find((item) => item.phase === renderPhaseFromProgress(progress)) ?? RENDER_PHASES[0]

const stagePercentWithinRange = (progress: number, start: number, end: number): number => {
  if (end <= start) return progress >= end ? 100 : 0
  const clamped = Math.min(end, Math.max(start, progress))
  return Math.round(((clamped - start) / (end - start)) * 100)
}

const stageDisplayPercent = (progress: number, meta: RenderPhaseMeta, isCurrent: boolean): number => {
  const pct = stagePercentWithinRange(progress, meta.start, meta.end)
  if (isCurrent && pct >= 100 && meta.phase !== 'done') {
    return 99
  }
  return pct
}

const estimatedSceneIndex = (progressPct: number, totalScenes: number): number => {
  if (totalScenes <= 0) return 0
  if (progressPct <= 0) return 1
  return Math.min(totalScenes, Math.max(1, Math.ceil((progressPct / 100) * totalScenes)))
}

const renderPhaseNarrative = (progress: number, scenes: ReviewScene[]) => {
  const meta = renderPhaseMetaForProgress(progress)
  const currentPhasePct = stagePercentWithinRange(progress, meta.start, meta.end)

  if (meta.phase === 'tts') {
    const sceneIndex = estimatedSceneIndex(currentPhasePct, scenes.length)
    const scene = scenes[sceneIndex - 1]
    return {
      headline: scene ? `Narración estimada: escena ${sceneIndex} de ${scenes.length}` : 'Narración en progreso',
      detail: scene ? `${scene.tag}: sintetizando el audio de esta escena.` : meta.description,
    }
  }

  if (meta.phase === 'visuals') {
    const sceneIndex = estimatedSceneIndex(currentPhasePct, scenes.length)
    const scene = scenes[sceneIndex - 1]
    const slowScenes = scenes
      .filter((item) => SLOW_VISUAL_TYPES.includes(item.visualType))
      .map((item) => VISUAL_META[item.visualType]?.tag ?? item.visualType)
    const slowHint = slowScenes.length > 0
      ? ` En este storyboard hay visuales más lentos: ${Array.from(new Set(slowScenes)).join(', ')}.`
      : ''
    const remotionHint = ' Los charts, comparisons, callouts, progress bars y terminales aparecen más tarde en la etapa de Render, no como archivos sueltos aquí.'
    return {
      headline: scene ? `Visual estimado: escena ${sceneIndex} de ${scenes.length}` : 'Visuales en progreso',
      detail: scene
        ? `${scene.tag} (${scene.visualType}): generando el asset visual de esta escena.${slowHint}${remotionHint}`
        : `${meta.description}${slowHint}${remotionHint}`,
    }
  }

  return {
    headline: meta.shortLabel,
    detail: meta.description,
  }
}

// Visual-type → friendly tag + pacing budget (mirrors ADR-0012 pacing rules).
const VISUAL_META: Record<VisualType, { tag: string; budget: number }> = {
  hero_title: { tag: 'Título inicial (Spring)', budget: 80 },
  text_card: { tag: 'Texto / Slide', budget: 120 },
  stat_card: { tag: 'Métrica Clave', budget: 120 },
  callout: { tag: 'Nota / Definición', budget: 120 },
  comparison: { tag: 'Comparación', budget: 140 },
  bar_chart: { tag: 'Gráfico de Barras', budget: 200 },
  line_chart: { tag: 'Gráfico de Líneas', budget: 200 },
  pie_chart: { tag: 'Gráfico Circular', budget: 200 },
  kpi_grid: { tag: 'Grid de KPIs', budget: 200 },
  progress_bar: { tag: 'Barra de Progreso', budget: 200 },
  terminal_scene: { tag: 'Demo CLI (Terminal)', budget: 240 },
  screenshot_scene: { tag: 'Walkthrough UI', budget: 240 },
  ai_video: { tag: 'Hook (Veo 3.1)', budget: 180 },
  ai_illustration: { tag: 'Ilustración (Imagen 3)', budget: 200 },
}

export const sceneToReviewScene = (
  scene: StoryboardScene,
  fallback: { groundingStatus?: GroundingStatus } = {},
): ReviewScene => {
  const vt = scene.visual_type ?? 'text_card'
  const meta = VISUAL_META[vt] ?? VISUAL_META.text_card
  return {
    sceneNumber: scene.scene_number,
    tag: meta.tag,
    budget: meta.budget,
    narration: scene.narration ?? '',
    visualType: vt,
    visualConfig: scene.visual_config ?? {},
    teachingPoint: scene.teaching_point ?? 'Revisar el objetivo didáctico de esta escena antes de renderizar.',
    pedagogicalIntent: scene.pedagogical_intent ?? 'Intención pendiente de confirmar.',
    teachingPattern: scene.teaching_pattern ?? 'Patrón didáctico no especificado.',
    visualRationale: scene.visual_rationale ?? 'Validar que este visual realmente ayude a aprender.',
    groundingStatus: scene.grounding_status ?? fallback.groundingStatus ?? 'module_grounded',
  }
}

export const updateSceneNarration = (scene: ReviewScene, narration: string): ReviewScene => ({
  ...scene,
  narration,
})

export const updateSceneVisualType = (scene: ReviewScene, visualType: VisualType): ReviewScene => {
  const meta = VISUAL_META[visualType] ?? VISUAL_META.text_card
  return {
    ...scene,
    visualType,
    tag: meta.tag,
    budget: meta.budget,
    visualConfig: {},
  }
}

export const buildReviewedStoryboard = (title: string, totalWordBudget: number, scenes: ReviewScene[]) => ({
  title,
  total_word_budget: totalWordBudget,
  scenes: scenes.map((scene) => ({
    scene_number: scene.sceneNumber,
    narration: scene.narration,
    visual_type: scene.visualType,
    visual_config: scene.visualConfig,
    teaching_point: scene.teachingPoint,
    pedagogical_intent: scene.pedagogicalIntent,
    teaching_pattern: scene.teachingPattern,
    visual_rationale: scene.visualRationale,
    grounding_status: scene.groundingStatus,
  })),
})

// Prefers verified sources whose title or URL contains keywords from the route's
// objective/topic. Falls back to any source URL, then customerContext, then google.com.
const firstWalkthroughUrl = (route: LearningRoute): string => {
  const verified = route.sources.filter((s) => s.verified && s.url)
  if (verified.length > 0) {
    const keywords = [route.name, route.objective].filter(Boolean).join(' ').toLowerCase()
    const best = verified.find((s) =>
      s.title?.toLowerCase().split(' ').some((w) => keywords.includes(w))
    )
    return best?.url ?? verified[0]?.url ?? ''
  }
  return route.sources.find((s) => s.url)?.url ?? route.customerContext?.url ?? ''
}


const buildReviewScenes = (route: LearningRoute): ReviewScene[] => {
  const lessonLead = route.pack.lesson.sections[0]?.body || route.objective || 'Capacitación integral en arquitectura de sistemas y flujos IA.'

  const verifiedSources = route.sources.filter((source) => source.verified).slice(0, 3)
  const sourceBullets = verifiedSources.length
    ? verifiedSources.map((source) => source.title).filter(Boolean)
    : [route.name, 'Documentación oficial y arquitectura']

  const cleanBullets = (...list: (string | undefined | null)[]) => {
    const res = list
      .map((x) => (x ? String(x).trim() : ''))
      .filter((x) => x.length > 0)
    return res.length > 0 ? res : ['Estrategia y ejecución continua', 'Monitoreo y estándares de calidad verificables']
  }

  return [
    {
      sceneNumber: 1,
      tag: 'Pregunta guía',
      budget: 120,
      narration: `¿Por qué es fundamental dominar ${route.name}? Conectamos su objetivo con el negocio.`,
      visualType: 'callout',
      visualConfig: {
        callout_style: 'info',
        text: `¿Por qué importa ${route.name}?`,
      },
      teachingPoint: `Conectar ${route.name} con una pregunta de aprendizaje concreta.`,
      pedagogicalIntent: 'Abrir el video con una pregunta útil, no con una intro decorativa.',
      teachingPattern: 'framing_question',
      visualRationale: 'Un callout deja explícita la pregunta guía sin fingir una metáfora visual todavía no validada.',
      groundingStatus: 'module_grounded',
    },
    {
      sceneNumber: 2,
      tag: 'Modelo mental inicial',
      budget: 160,
      narration: `Para entender los cimientos técnicos, examinamos la arquitectura de la solución: ${lessonLead}`,
      visualType: 'text_card',
      visualConfig: {
        title: route.name,
        subtitle: cleanBullets(route.pack.video.caption, ...sourceBullets).join(' • '),
      },
      teachingPoint: 'Construir un modelo mental inicial del tema.',
      pedagogicalIntent: 'Convertir el objetivo del módulo en una estructura visible.',
      teachingPattern: 'modelo mental',
      visualRationale: 'Una tarjeta de texto deja claro el modelo mental sin depender de una ilustración genérica.',
      groundingStatus: 'module_grounded',
    },
    {
      sceneNumber: 3,
      tag: 'Pilares Clave (Progreso)',
      budget: 180,
      narration: 'Desglosamos las etapas fundamentales que sustentan este flujo para asegurar la calidad.',
      visualType: 'progress_bar',
      visualConfig: {
        title: 'Pilares del Sistema',
        progress: 60,
        steps: cleanBullets(
          route.pack.lesson.sections[0]?.heading,
          route.pack.lesson.sections[1]?.heading,
          route.pack.lesson.sections[2]?.heading,
          'Control de calidad y verificación humana por compuertas'
        ),
      },
      teachingPoint: 'Mostrar el proceso como una secuencia de decisiones.',
      pedagogicalIntent: 'Ayudar al estudiante a ubicar cada paso dentro del flujo completo.',
      teachingPattern: 'explicación de proceso',
      visualRationale: 'La barra de progreso comunica orden y avance sin inventar métricas.',
      groundingStatus: 'module_grounded',
    },
    {
      sceneNumber: 4,
      tag: 'Walkthrough pendiente',
      budget: 140,
      narration: 'Veamos cómo se ejecuta esto en la práctica dentro del entorno real.',
      visualType: 'callout',
      visualConfig: {
        callout_style: 'warning',
        text: firstWalkthroughUrl(route)
          ? 'Validar URL específica, pasos y resultado antes de grabar un walkthrough real.'
          : 'Falta una URL verificable para convertir esta escena en un walkthrough didáctico.',
      },
      teachingPoint: 'Anclar el concepto en una acción observable.',
      pedagogicalIntent: 'Revisar si existe una URL y pasos reales antes de gastar render.',
      teachingPattern: 'demostración práctica',
      visualRationale: 'Sin URL y pasos validados, un callout evita fingir una demostración de UI.',
      groundingStatus: 'module_grounded',
    },
    {
      sceneNumber: 5,
      tag: 'Decisión final',
      budget: 160,
      narration: 'Para finalizar, es momento de llevar este conocimiento a la ejecución y medir la eficiencia.',
      visualType: 'comparison',
      visualConfig: {
        leftLabel: 'Sin criterio',
        leftValue: 'Más retrabajo y menos claridad',
        rightLabel: 'Con criterio',
        rightValue: 'Mejor decisión y ejecución más consistente',
      },
      teachingPoint: 'Cerrar con una decisión accionable para aplicar el concepto.',
      pedagogicalIntent: 'Convertir el aprendizaje en criterio de ejecución.',
      teachingPattern: 'synthesis',
      visualRationale: 'La comparación cierra con un contraste útil sin inventar métricas.',
      groundingStatus: 'module_grounded',
    },
  ]
}

export default function Storyboard() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const searchParams = useSearchParams()
  const moduleId = searchParams.get('module_id') ?? undefined
  const {
    routes,
    approveStoryboard,
    storyboardVideoUrlOf,
    setStoryboardVideoUrl,
    storyboardJobIdOf,
    setStoryboardJobId,
    clearStoryboardJobId,
  } = useStore()
  const route = routes.find((item) => item.id === id) ?? getRoute(id)
  const defaultReviewScenes = useMemo(() => (route ? buildReviewScenes(route) : []), [route])
  const hasValidRenderTarget = hasRenderTargetModuleId(moduleId)

  // Video generation/render states
  const [renderingState, setRenderingState] = useState<'idle' | 'rendering' | 'success' | 'failed'>('idle')
  const [renderProgress, setRenderProgress] = useState(0)
  const [videoUrl, setVideoUrl] = useState('')
  const [reviewScenes, setReviewScenes] = useState<ReviewScene[]>(defaultReviewScenes)
  const [isEditing, setIsEditing] = useState(false)
  const [storyboardLoading, setStoryboardLoading] = useState(false)
  const [storyboardSource, setStoryboardSource] = useState<StoryboardSource>(
    hasValidRenderTarget ? 'idle' : 'fallback_invalid_target',
  )
  const [storyboardGrounding, setStoryboardGrounding] = useState<{
    status: GroundingStatus | null
    chunkCount: number
  }>({ status: null, chunkCount: 0 })

  const loadStoryboard = async (announceSuccess = false) => {
    if (!route) return false
    if (!hasValidRenderTarget) {
      setStoryboardSource('fallback_invalid_target')
      setStoryboardGrounding({ status: null, chunkCount: 0 })
      return false
    }

    setStoryboardLoading(true)
    try {
      const data = await api.request<{
        storyboard: { scenes?: StoryboardScene[] }
        grounding?: { status?: GroundingStatus; chunks?: unknown[] }
      }>(
        '/videos/storyboard',
        {
          method: 'POST',
          body: JSON.stringify({ route_id: route.id, module_id: moduleId }),
        },
      )

      const scenes = Array.isArray(data?.storyboard?.scenes) ? data.storyboard.scenes : []
      const groundingStatus = data?.grounding?.status ?? null
      const chunkCount = Array.isArray(data?.grounding?.chunks) ? data.grounding.chunks.length : 0
      setStoryboardGrounding({ status: groundingStatus, chunkCount })

      if (scenes.length > 0) {
        setReviewScenes(scenes.map((scene) => sceneToReviewScene(scene, { groundingStatus: data.grounding?.status })))
        setStoryboardSource('backend')
        if (announceSuccess) {
          toast.success('Guion regenerado desde el backend', { id: 'storyboard-fetch' })
        }
        return true
      }

      setStoryboardSource('fallback_empty')
      toast.error('El backend no devolvió escenas renderizables. Se mantiene el borrador actual para que puedas renderizar o volver a intentar.', {
        id: 'storyboard-fetch',
      })
      return false
    } catch {
      setStoryboardSource('fallback_error')
      setStoryboardGrounding({ status: null, chunkCount: 0 })
      toast.error('No se pudo cargar el storyboard del backend. Se mantiene el borrador actual para que puedas renderizar o volver a intentar.', {
        id: 'storyboard-fetch',
      })
      return false
    } finally {
      setStoryboardLoading(false)
    }
  }

  const savedVideoUrl = route ? storyboardVideoUrlOf(route.id) : ''
  const savedJobId = route ? storyboardJobIdOf(route.id) : undefined
  const resolvedVideoUrl = videoUrl || savedVideoUrl
  const syncPersistedVideoAsset = useCallback(
    async () => {
      if (!route || !moduleId || !hasValidRenderTarget) return ''
      try {
        const finalUrl = await fetchRenderedVideoAssetUrl(route.id, moduleId)
        if (!finalUrl) return ''
        setVideoUrl(finalUrl)
        setStoryboardVideoUrl(route.id, finalUrl)
        return finalUrl
      } catch {
        return ''
      }
    },
    [route, moduleId, hasValidRenderTarget, setStoryboardVideoUrl],
  )

  useEffect(() => {
    if (!route || !moduleId || !hasValidRenderTarget) return
    let active = true
    syncPersistedVideoAsset()
      .then((finalUrl) => {
        if (!active) return
        if (!finalUrl) return
        setRenderProgress(100)
        setRenderingState('success')
        clearStoryboardJobId(route.id)
      })

    return () => {
      active = false
    }
  }, [route, moduleId, hasValidRenderTarget, syncPersistedVideoAsset, clearStoryboardJobId])

  useEffect(() => {
    setReviewScenes(defaultReviewScenes)
    setIsEditing(false)
    setRenderingState('idle')
    setRenderProgress(0)
    setVideoUrl('')
    setStoryboardSource(hasValidRenderTarget ? 'idle' : 'fallback_invalid_target')
    setStoryboardGrounding({ status: null, chunkCount: 0 })
  }, [defaultReviewScenes, route?.id, hasValidRenderTarget])

  useEffect(() => {
    if (!route) return

    let active = true

    const resume = async () => {
      if (savedVideoUrl) {
        setVideoUrl(savedVideoUrl)
        setRenderProgress(100)
        setRenderingState('success')
        clearStoryboardJobId(route.id)
        return
      }

      if (!savedJobId) return

      setRenderingState('rendering')
      setRenderProgress(5)

      const poll = async () => {
        if (!active) return

        try {
          const status = await api.request<{ status: string, progress: number, result?: { video_url?: string; videoUrl?: string } }>(
            `/videos/jobs/${savedJobId}`,
          )
          if (!active) return

          setRenderProgress(status.progress)

          if (status.status === 'completed') {
            const finalUrl = status.result?.video_url || status.result?.videoUrl || ''
            setRenderingState('success')
            setVideoUrl(finalUrl)
            if (finalUrl) {
              setStoryboardVideoUrl(route.id, finalUrl)
            }
            clearStoryboardJobId(route.id)
            approveStoryboard(route.id)
            return
          }

          if (status.status === 'failed') {
            setRenderingState('failed')
            clearStoryboardJobId(route.id)
            return
          }

          setRenderingState('rendering')
          window.setTimeout(poll, 1500)
        } catch {
          if (!active) return
          window.setTimeout(poll, 2000)
        }
      }

      void poll()
    }

    void resume()

    return () => {
      active = false
    }
  }, [
    route,
    savedJobId,
    savedVideoUrl,
    activeStoryboardJob,
    trackJob,
    setStoryboardVideoUrl,
    clearStoryboardJobId,
    approveStoryboard,
  ])

  useEffect(() => {
    if (!route || !savedJobId) return

    if (!activeStoryboardJob) {
      setRenderingState('rendering')
      setRenderProgress((current) => (current > 0 ? current : 5))
      return
    }

    setRenderProgress(activeStoryboardJob.progress)

    if (activeStoryboardJob.status === 'completed') {
      void (async () => {
        const finalUrl =
          renderedVideoUrlFromAsset(activeStoryboardJob.result as RenderedVideoAsset) ||
          activeStoryboardJob.result?.videoUrl ||
          await syncPersistedVideoAsset()
        setRenderingState('success')
        if (finalUrl) {
          setVideoUrl(finalUrl)
          setStoryboardVideoUrl(route.id, finalUrl)
        }
        clearStoryboardJobId(route.id)
        approveStoryboard(route.id)
        toast.success('¡Video generado con éxito!', { id: 'render-job' })
      })()
      return
    }

    if (activeStoryboardJob.status === 'failed') {
      setRenderingState('failed')
      clearStoryboardJobId(route.id)
      toast.error('La generación del video falló', { id: 'render-job' })
      return
    }

    setRenderingState('rendering')
  }, [
    route,
    savedJobId,
    activeStoryboardJob,
    syncPersistedVideoAsset,
    setStoryboardVideoUrl,
    clearStoryboardJobId,
    approveStoryboard,
  ])

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

  const totalBudget = reviewScenes.reduce((sum, scene) => sum + scene.budget, 0)
  const totalWords = reviewScenes.reduce((sum, scene) => sum + wordCount(scene.narration), 0)
  const canRenderCurrentStoryboard = canRenderAiStoryboard(storyboardSource)
  const hasExistingRender = Boolean(resolvedVideoUrl || savedJobId || renderingState === 'success' || renderingState === 'failed')
  const currentRenderPhase = renderPhaseFromProgress(renderProgress)
  const currentRenderMeta = renderPhaseMetaForProgress(renderProgress)
  const currentRenderNarrative = renderPhaseNarrative(renderProgress, reviewScenes)

  const startRender = async () => {
    if (!canRenderCurrentStoryboard) {
      toast.error('Este módulo todavía no tiene un render target válido para lanzar el video.')
      return
    }
    setRenderingState('rendering')
    setRenderProgress(5)
    toast.loading('Iniciando render del video...', { id: 'render-job' })
    
    try {
      const res = await api.request<{ job_id: string }>('/videos/generate', {
        method: 'POST',
        body: JSON.stringify({
          route_id: route.id,
          module_id: moduleId,
          component_kind: 'video',
          component_id: null,
          custom_storyboard: buildReviewedStoryboard(route.name, totalBudget, reviewScenes),
          use_mock: false
        })
      })
      const jId = res.job_id
      setStoryboardJobId(route.id, jId)

      const poll = async () => {
        try {
          const status = await api.request<{ status: string, progress: number, result?: { video_url: string } }>(
            `/videos/jobs/${jId}`
          )
          setRenderProgress(status.progress)
          
          if (status.status === 'completed') {
            const finalUrl = status.result?.video_url || ''
            setRenderingState('success')
            setVideoUrl(finalUrl)
            if (finalUrl) {
              setStoryboardVideoUrl(route.id, finalUrl)
            }
            clearStoryboardJobId(route.id)
            approveStoryboard(route.id)
            toast.success('¡Video generado con éxito!', { id: 'render-job' })
          } else if (status.status === 'failed') {
            setRenderingState('failed')
            clearStoryboardJobId(route.id)
            toast.error('La generación del video falló', { id: 'render-job' })
          } else {
            setTimeout(poll, 1500)
          }
        } catch (err) {
          setTimeout(poll, 2000)
        }
      }
      setTimeout(poll, 1000)

    } catch (e) {
      setRenderingState('failed')
      toast.error('No se pudo conectar con el servicio de renderizado', { id: 'render-job' })
    }
  }

  const approve = () => {
    approveStoryboard(route.id)
    toast.success('Guion y storyboard aprobados', {
      description: 'El video quedó guardado y listo en la ruta.',
    })
    router.push(`/ruta/${route.id}`)
  }

  return (
    <div className="mx-auto max-w-[860px]">
      <PageTitle>Configurar material audiovisual</PageTitle>
      <PageDescription className="mb-6">
        Genera y revisa el storyboard del módulo antes de lanzar el render final.
      </PageDescription>
      <>
          {renderingState !== 'idle' && (
            <Card className="mb-8 p-5 border-primary bg-primary/4 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {renderingState === 'rendering' && <Loader2 className="size-5 text-primary animate-spin" />}
                  {renderingState === 'success' && <CheckCircle2 className="size-5 text-success" />}
                  {renderingState === 'failed' && <AlertTriangle className="size-5 text-destructive" />}
                  <span className="font-display text-sm font-semibold text-ink">
                    {renderingState === 'rendering' && renderPhaseLabel(renderProgress)}
                    {renderingState === 'success' && '¡Generación Completada!'}
                    {renderingState === 'failed' && 'Error al Generar el Video'}
                  </span>
                </div>
                <span className="font-mono text-xs text-muted-foreground">
                  Progreso: {renderProgress}%
                </span>
              </div>
              
              <Progress value={renderProgress} indicatorClassName="bg-primary animate-pulse" className="h-2" />

              {renderingState === 'rendering' && (
                <div className="grid gap-3 sm:grid-cols-[1.1fr_0.9fr]">
                  <div className="rounded-xl border border-primary/20 bg-background/70 p-4">
                    <div className="text-[13px] font-semibold text-ink">
                      {currentRenderNarrative.headline}
                    </div>
                    <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                      {currentRenderNarrative.detail}
                    </p>
                    {savedJobId && (
                      <div className="mt-3 text-[11px] text-muted-foreground">
                        Job ID: <span className="font-mono">{savedJobId}</span>
                      </div>
                    )}
                  </div>
                  <div className="rounded-xl border border-primary/20 bg-background/70 p-4">
                    <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                      Pipeline
                    </div>
                    <div className="space-y-2">
                      {RENDER_PHASES.filter((item) => item.phase !== 'done').map((item) => {
                        const isDone = item.end < renderProgress
                        const isCurrent = item.phase === currentRenderPhase
                        return (
                          <div
                            key={item.phase}
                            className={`flex items-center justify-between rounded-lg px-2.5 py-2 text-[12px] ${
                              isCurrent
                                ? 'bg-primary/10 text-ink'
                                : isDone
                                  ? 'bg-emerald-50 text-emerald-700'
                                  : 'bg-muted/40 text-muted-foreground'
                            }`}
                          >
                            <span className="font-medium">{item.shortLabel}</span>
                            <span className="font-mono">
                              {isDone ? 'ok' : isCurrent ? `${stageDisplayPercent(renderProgress, item, isCurrent)}%` : '...'}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                    <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
                      {currentRenderMeta.description}
                    </p>
                  </div>
                </div>
              )}

              {renderingState === 'success' && resolvedVideoUrl && (
                <div className="mt-2 rounded-lg overflow-hidden border border-secondary bg-black aspect-video flex flex-col justify-center items-center">
                  <video src={resolvedVideoUrl} controls className="w-full h-full object-cover" />
                </div>
              )}
              {renderingState === 'success' && !resolvedVideoUrl && (
                <div className="mt-2 rounded-lg border border-dashed border-secondary bg-background px-4 py-6 text-center text-sm text-muted-foreground">
                  Video list. URL faltante. Revisa backend result o refresca una vez más.
                </div>
              )}
            </Card>
          )}

          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="mb-1 font-display text-lg font-medium text-ink">Storyboard del video</h2>
              <p className="text-[13px] text-muted-foreground">
                {storyboardSource === 'backend' ? 'Versión ligada a la ruta real.' : 'Borrador listo para usar.'} Objetivo {route.pack.video.duration || '02:00'} · {totalWords} palabras totales.
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-start gap-3 sm:justify-end">
              <Button
                variant={storyboardSource === 'backend' ? 'outline' : 'default'}
                onClick={async () => {
                  setIsEditing(false)
                  if (!route || !hasValidRenderTarget) {
                    toast.warning('Este render target sigue siendo local. Abre un módulo persistido para generar el storyboard real.')
                    return
                  }
                  await loadStoryboard(storyboardSource === 'backend')
                }}
                disabled={storyboardLoading}
                className="gap-2"
              >
                {storyboardLoading ? <Loader2 className="animate-spin" /> : <RefreshCcw />}
                {storyboardLoading ? 'Generando storyboard…' : storyboardSource === 'backend' ? 'Regenerar storyboard' : 'Generar storyboard'}
              </Button>
              <Button variant="outline" onClick={() => setIsEditing((value) => !value)} className="gap-2">
                <SquarePen /> {isEditing ? 'Listo' : 'Editar storyboard'}
              </Button>
              <Button
                onClick={startRender}
                disabled={storyboardLoading || !canRenderCurrentStoryboard || renderingState === 'rendering'}
                className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {renderingState === 'rendering' ? <Loader2 className="animate-spin" /> : <Film />}
                {storyboardLoading
                  ? 'Cargando storyboard…'
                  : canRenderCurrentStoryboard
                    ? renderActionLabel(renderingState, hasExistingRender)
                    : 'Requiere módulo real'}
              </Button>
              <Button onClick={approve} disabled={renderingState === 'rendering'} className="gap-2">
                <Check /> Guardar y Volver <ArrowRight />
              </Button>
            </div>
          </div>
          {storyboardLoading && (
            <Card className="mb-4 flex-row items-start gap-3 border-primary/20 bg-primary/5 p-4">
              <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  Generando storyboard
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  Estamos llamando al backend del módulo. Cuando termine, aquí verás el storyboard listo para revisión.
                </p>
              </div>
            </Card>
          )}
          {!storyboardLoading && storyboardSource === 'idle' && hasValidRenderTarget && (
            <Card className="mb-4 flex-row items-start gap-3 border-primary/20 bg-primary/5 p-4">
              <Info className="mt-0.5 size-4 shrink-0 text-primary" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  Borrador listo para renderizar
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  Ya puedes renderizar este borrador inmediatamente. Si quieres reemplazarlo con una versión específica del backend para este módulo, usa <span className="font-mono">POST /videos/storyboard</span> con el botón de arriba.
                </p>
              </div>
            </Card>
          )}
          {storyboardSource === 'backend' && (
            <Card className="mb-4 flex-row items-start gap-3 border-emerald-300/60 bg-emerald-50/70 p-4">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  Storyboard listo
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  {storyboardGrounding.status === 'kb_grounded'
                    ? `El backend devolvió un storyboard real con ${storyboardGrounding.chunkCount} chunk${storyboardGrounding.chunkCount === 1 ? '' : 's'} de grounding para este módulo.`
                    : 'El backend devolvió un storyboard real para este módulo. Ya puedes revisarlo y lanzar el render cuando quede bien.'}
                </p>
              </div>
            </Card>
          )}
          {!hasValidRenderTarget && (
            <Card className="mb-4 flex-row items-start gap-3 border-amber-300/60 bg-amber-50/70 p-4">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  Storyboard local: falta un Render Target real
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  Esta página solo llama a
                  <span className="font-mono"> POST /videos/storyboard</span> cuando la ruta es persistida y existe un <span className="font-mono">module_id</span>. Ruta: {route.id}. Módulo: {moduleId ?? 'sin module_id'}.
                </p>
              </div>
            </Card>
          )}
          {storyboardSource === 'fallback_error' && hasValidRenderTarget && (
            <Card className="mb-4 flex-row items-start gap-3 border-destructive/30 bg-destructive/5 p-4">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  No se pudo cargar el storyboard del backend
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  La llamada a <span className="font-mono">POST /videos/storyboard</span> falló. Puedes seguir con el borrador actual o volver a intentarlo.
                </p>
              </div>
            </Card>
          )}
          {storyboardSource === 'fallback_empty' && hasValidRenderTarget && (
            <Card className="mb-4 flex-row items-start gap-3 border-destructive/30 bg-destructive/5 p-4">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  El backend no produjo escenas nuevas
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  Se mantiene el borrador actual para que puedas renderizarlo o volver a pedir una versión del backend.
                </p>
              </div>
            </Card>
          )}

          <div className="mb-8 flex flex-col gap-3.5">
            {reviewScenes.map((scene, index) => {
              const used = wordCount(scene.narration)
              const pct = Math.min(100, Math.round((used / scene.budget) * 100))
              return (
                <Card key={`${scene.sceneNumber}-${scene.tag}`} className="gap-3 p-4.5">
                  <div className="flex items-center justify-between">
                    <Badge>{scene.tag}</Badge>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {used} / {scene.budget} palabras
                    </span>
                  </div>
                  <div className="grid gap-2 rounded-lg border border-secondary bg-muted/20 p-3 text-[12px] leading-relaxed sm:grid-cols-2">
                    <div>
                      <span className="font-semibold text-ink">Punto didáctico: </span>
                      <span className="text-muted-foreground">{scene.teachingPoint}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-ink">Grounding: </span>
                      <span className="font-mono text-muted-foreground">{scene.groundingStatus}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-ink">Patrón: </span>
                      <span className="text-muted-foreground">{scene.teachingPattern}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-ink">Intención: </span>
                      <span className="text-muted-foreground">{scene.pedagogicalIntent}</span>
                    </div>
                    <div className="sm:col-span-2">
                      <span className="font-semibold text-ink">Razón visual: </span>
                      <span className="text-muted-foreground">{scene.visualRationale}</span>
                    </div>
                  </div>
                  {isEditing ? (
                    <>
                      <div className="flex items-center gap-3">
                        <label className="shrink-0 text-[11px] font-medium text-muted-foreground">
                          Tipo visual:
                        </label>
                        <select
                          value={scene.visualType}
                          onChange={(e) => {
                            setReviewScenes((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === index
                                  ? updateSceneVisualType(item, e.target.value as VisualType)
                                  : item,
                              ),
                            )
                          }}
                          className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-xs shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        >
                          {(Object.keys(VISUAL_META) as VisualType[]).map((type) => (
                            <option key={type} value={type}>
                              {VISUAL_META[type].tag} — {type}
                            </option>
                          ))}
                        </select>
                      </div>
                      <Textarea
                        value={scene.narration}
                        onChange={(event) => {
                          setReviewScenes((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index ? updateSceneNarration(item, event.target.value) : item
                            )
                          )
                        }}
                        rows={5}
                        className="text-sm leading-relaxed"
                      />
                    </>
                  ) : (
                    <p className="text-sm leading-relaxed">{scene.narration}</p>
                  )}
                  <Progress value={pct} indicatorClassName="bg-success" className="h-1.25" />
                </Card>
              )
            })}
          </div>

      </>

      <Card className="mb-6 flex-row items-start gap-3.5 border-accent bg-primary/8 p-4.5">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <div className="mb-1 text-[13.5px] font-semibold text-ink">
            Generación Híbrida Inteligente
          </div>
          <p className="text-[13px] leading-relaxed">
            Este storyboard editable es el mismo que se envía al pipeline de render. Si generas una versión desde el backend, reemplaza este borrador con esa propuesta antes de renderizar.
          </p>
        </div>
      </Card>
    </div>
  )
}
