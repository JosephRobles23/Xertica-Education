'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { ArrowRight, Check, Info, RefreshCcw, SquarePen, Film, CheckCircle2, AlertTriangle, Loader2, Link2, Scissors } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Progress } from '@/shared/ui/progress'
import { Textarea } from '@/shared/ui/textarea'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { getRoute } from '@/shared/data/routes'
import type { LearningRoute } from '@/shared/lib/types'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'

export type VisualType = 'text_card' | 'hero_title' | 'stat_card' | 'callout' | 'comparison' | 'bar_chart' | 'line_chart' | 'pie_chart' | 'kpi_grid' | 'progress_bar' | 'terminal_scene' | 'screenshot_scene' | 'ai_video' | 'ai_illustration'

type GroundingStatus = 'kb_grounded' | 'module_grounded'
type StoryboardSource = 'backend' | 'fallback_invalid_target' | 'fallback_error' | 'fallback_empty'
type RenderedVideoAsset = {
  storage_path?: string | null
  video_url?: string | null
}
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

const wordCount = (text: string) => text.trim().split(/\s+/).filter(Boolean).length
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export const isValidUuid = (value: string | undefined): value is string => Boolean(value && UUID_PATTERN.test(value))
export const hasRenderTargetModuleId = (moduleId: string | undefined): moduleId is string => Boolean(moduleId && moduleId.trim().length > 0)
export const canRenderAiStoryboard = (storyboardSource: StoryboardSource) => storyboardSource === 'backend'

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
  switch (phase) {
    case 'tts':
      return 'Sintetizando narración por escena...'
    case 'visuals':
      return 'Preparando visuales y capturas...'
    case 'music':
      return 'Buscando música de fondo...'
    case 'timeline':
      return 'Armando el plan de edición...'
    case 'render':
      return 'Renderizando video final en Remotion...'
    case 'validate':
      return 'Validando duración y archivo final...'
    case 'upload':
      return 'Subiendo el MP4 final...'
    case 'done':
      return '¡Generación Completada!'
    default:
      return 'Encolando render en la nube...'
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

const videoUrlFromAsset = (asset: RenderedVideoAsset) => asset.storage_path || asset.video_url || ''

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
    hasValidRenderTarget ? 'fallback_error' : 'fallback_invalid_target',
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
      toast.error('El backend no devolvió escenas renderizables. Se bloquea el render para evitar un video genérico.', {
        id: 'storyboard-fetch',
      })
      return false
    } catch {
      setStoryboardSource('fallback_error')
      setStoryboardGrounding({ status: null, chunkCount: 0 })
      toast.error('No se pudo cargar el storyboard real. Se bloquea el render para evitar un video genérico.', {
        id: 'storyboard-fetch',
      })
      return false
    } finally {
      setStoryboardLoading(false)
    }
  }

  // Fetch a KB-grounded storyboard from /videos/storyboard when a module_id is
  // present in the URL (ADR-0015). Falls back to local default script on error
  // or when no module context is available, so the page stays usable.
  useEffect(() => {
    let active = true
    const fetchStoryboard = async () => {
      if (!route || !active) return
      const loaded = await loadStoryboard(false)
      if (!active || !loaded) return
      toast.success('Guion generado con base de conocimiento', { id: 'storyboard-fetch' })
    }
    void fetchStoryboard()
    return () => { active = false }
  }, [route?.id, moduleId, hasValidRenderTarget])

  // Video reuse / segmentation states
  const [existingVideoUrl, setExistingVideoUrl] = useState('')
  const [segmenting, setSegmenting] = useState(false)
  const [segments, setSegments] = useState<any[]>([])
  const [selectedSegment, setSelectedSegment] = useState<any>(null)
  const savedVideoUrl = route ? storyboardVideoUrlOf(route.id) : ''
  const savedJobId = route ? storyboardJobIdOf(route.id) : undefined
  const resolvedVideoUrl = videoUrl || savedVideoUrl

  useEffect(() => {
    if (!route || !moduleId || !hasValidRenderTarget) return
    let active = true
    const params = new URLSearchParams({
      route_id: route.id,
      module_id: moduleId,
      component_kind: 'video',
    })

    api.request<RenderedVideoAsset>(`/videos/assets?${params.toString()}`)
      .then((asset) => {
        if (!active) return
        const finalUrl = videoUrlFromAsset(asset)
        if (!finalUrl) return
        setVideoUrl(finalUrl)
        setStoryboardVideoUrl(route.id, finalUrl)
        setRenderProgress(100)
        setRenderingState('success')
        clearStoryboardJobId(route.id)
      })
      .catch(() => {})

    return () => {
      active = false
    }
  }, [route, moduleId, hasValidRenderTarget, setStoryboardVideoUrl, clearStoryboardJobId])

  useEffect(() => {
    setReviewScenes(defaultReviewScenes)
    setIsEditing(false)
    setRenderingState('idle')
    setRenderProgress(0)
    setVideoUrl('')
    setSegments([])
    setSelectedSegment(null)
    setStoryboardSource(hasValidRenderTarget ? 'fallback_error' : 'fallback_invalid_target')
    setStoryboardGrounding({ status: null, chunkCount: 0 })
  }, [defaultReviewScenes, route?.id])

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
  const storyboardScenes = reviewScenes.map((scene, index) => {
    const routeSegment = route.pack.video.segments[index]
    return {
      index,
      title: scene.tag,
      at: routeSegment?.at ?? `00:${String(index * 24).padStart(2, '0')}`,
      excerpt: scene.narration,
      visualType: scene.visualType,
      teachingPoint: scene.teachingPoint,
      pedagogicalIntent: scene.pedagogicalIntent,
      teachingPattern: scene.teachingPattern,
      visualRationale: scene.visualRationale,
      groundingStatus: scene.groundingStatus,
    }
  })

  const runSegmentation = async () => {
    if (!existingVideoUrl) {
      toast.error('Por favor ingresa una URL de video válida')
      return
    }
    setSegmenting(true)
    toast.loading('Analizando y segmentando video de entrenamiento...', { id: 'segment-job' })
    
    try {
      const data = await api.request<{ segments: any[] }>('/videos/segment', {
        method: 'POST',
        body: JSON.stringify({ video_url: existingVideoUrl })
      })
      setSegments(data.segments)
      toast.success('¡Video segmentado con éxito!', { id: 'segment-job' })
    } catch (e) {
      toast.error('No se pudo procesar el video de entrenamiento', { id: 'segment-job' })
    } finally {
      setSegmenting(false)
    }
  }

  const startRender = async () => {
    if (!canRenderCurrentStoryboard) {
      toast.error('Primero carga un storyboard real desde el backend. El render local está bloqueado para evitar un video genérico.')
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
      description: selectedSegment 
        ? `Reutilizando segmento: ${selectedSegment.title}`
        : 'El video quedó guardado y listo en la ruta.',
    })
    router.push(`/ruta/${route.id}`)
  }

  return (
    <div className="mx-auto max-w-[860px]">
      <Eyebrow tone="primary">
        Ruta {route.id} · Video · Configuración de Asset
      </Eyebrow>
      <PageTitle>Configurar material audiovisual</PageTitle>
      <PageDescription className="mb-6">
        Selecciona si deseas generar un video interactivo con IA o reutilizar material pregrabado de entrenamiento.
      </PageDescription>

      {/* SECTION 1: INGEST EXISTING TRAINING VIDEO */}
      <Card className="mb-8 p-5 border-secondary bg-background gap-4">
        <h3 className="font-display text-base font-semibold text-ink flex items-center gap-2">
          <Link2 className="size-4 text-primary" /> Reutilizar Video de Entrenamiento Existente
        </h3>
        <p className="text-xs text-muted-foreground">
          Pega el link de una sesión grabada de Meet, Drive o YouTube. El agente extraerá el audio, lo transcribirá y lo segmentará por temas para que elijas qué sección recortar.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={existingVideoUrl}
            onChange={(e) => setExistingVideoUrl(e.target.value)}
            placeholder="Ej: https://drive.google.com/file/d/... o enlace Meet"
            className="flex-1 rounded-lg border border-input bg-background px-3 py-1.75 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
          <Button disabled={segmenting} onClick={runSegmentation} variant="outline" className="shrink-0 gap-1.5">
            {segmenting ? <Loader2 className="size-3.5 animate-spin" /> : <Scissors className="size-3.5" />}
            Segmentar Video
          </Button>
        </div>

        {/* Display Segmented Topics */}
        {segments.length > 0 && (
          <div className="mt-4 flex flex-col gap-2.5">
            <h4 className="font-display text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Temas detectados para recorte:
            </h4>
            <div className="grid gap-3 sm:grid-cols-2">
              {segments.map((seg) => {
                const isSelected = selectedSegment?.id === seg.id
                return (
                  <Card
                    key={seg.id}
                    onClick={() => setSelectedSegment(seg)}
                    className={`cursor-pointer p-4 transition-all hover:scale-[1.01] ${
                      isSelected 
                        ? 'border-success bg-success/4 ring-1 ring-success' 
                        : 'border-secondary hover:border-accent'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <span className="font-display text-xs font-semibold text-ink leading-snug">
                        {seg.title}
                      </span>
                      <Badge variant={isSelected ? 'default' : 'outline'} className="font-mono text-[9px] px-1.5 py-0.5">
                        {seg.start} - {seg.end}
                      </Badge>
                    </div>
                    <p className="text-[11.5px] leading-relaxed text-muted-foreground">
                      {seg.summary}
                    </p>
                  </Card>
                )
              })}
            </div>
          </div>
        )}
      </Card>

      {/* Selected Segment Banner */}
      {selectedSegment && (
        <Card className="mb-8 p-4.5 border-success bg-success/8 flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="size-5 text-success shrink-0" />
            <div>
              <div className="text-[13px] font-semibold text-success">
                Segmento de video seleccionado
              </div>
              <p className="text-[11.5px] text-muted-foreground leading-relaxed">
                «{selectedSegment.title}» ({selectedSegment.start} a {selectedSegment.end}) se guardará como el video del módulo.
              </p>
            </div>
          </div>
          <Button onClick={() => setSelectedSegment(null)} size="sm" variant="outline" className="border-success/30 text-success hover:bg-success/10 text-xs py-1 h-7">
            Quitar
          </Button>
        </Card>
      )}

      {/* SECTION 2: AI STORYBOARD & RENDER */}
      {!selectedSegment && (
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

          <h2 className="mb-1 font-display text-lg font-medium text-ink">Guion segmentado por IA</h2>
          <p className="mb-4 text-[13px] text-muted-foreground">
            {storyboardSource === 'backend' ? 'Guion ligado a la ruta real.' : 'Borrador local de referencia.'} Objetivo {route.pack.video.duration || '02:00'} · {totalWords} palabras totales.
          </p>
          {storyboardSource === 'backend' && storyboardGrounding.status === 'kb_grounded' && (
            <Card className="mb-4 flex-row items-start gap-3 border-emerald-300/60 bg-emerald-50/70 p-4">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  Storyboard KB-grounded activo
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  El backend devolvió un storyboard real con {storyboardGrounding.chunkCount} chunk{storyboardGrounding.chunkCount === 1 ? '' : 's'} de grounding para este módulo.
                </p>
              </div>
            </Card>
          )}
          {storyboardSource === 'backend' && storyboardGrounding.status === 'module_grounded' && (
            <Card className="mb-4 flex-row items-start gap-3 border-amber-300/60 bg-amber-50/70 p-4">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  Storyboard real, pero sin grounding útil de KB
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  El backend sí generó el storyboard del módulo, pero no encontró chunks útiles en la KB. Por ADR, eso normalmente significa que esta ruta no tiene documentos Vía 2 ingeridos para este tema.
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
                  Storyboard real no disponible
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  La llamada a <span className="font-mono">POST /videos/storyboard</span> falló. El render queda bloqueado para no producir un video genérico desconectado de la KB y del módulo real.
                </p>
              </div>
            </Card>
          )}
          {storyboardSource === 'fallback_empty' && hasValidRenderTarget && (
            <Card className="mb-4 flex-row items-start gap-3 border-destructive/30 bg-destructive/5 p-4">
              <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
              <div>
                <div className="text-[13px] font-semibold text-ink">
                  El backend no produjo escenas renderizables
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
                  Se mantiene un borrador local de referencia, pero el render queda bloqueado hasta que exista un storyboard real del backend.
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
                  ) : (
                    <p className="text-sm leading-relaxed">{scene.narration}</p>
                  )}
                  <Progress value={pct} indicatorClassName="bg-success" className="h-1.25" />
                </Card>
              )
            })}
          </div>

          <h2 className="mb-1 font-display text-lg font-medium text-ink">Storyboard Propuesto</h2>
          <p className="mb-4 text-[13px] text-muted-foreground">
            {storyboardScenes.length} escenas · orden claro antes del render.
          </p>
          <div className="mb-8 flex flex-col gap-3.5">
            {storyboardScenes.map((scene) => (
              <Card key={`${scene.at}-${scene.title}`} className="gap-3 p-4.5">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 font-mono text-[12px] font-semibold text-primary">
                      {String(scene.index + 1).padStart(2, '0')}
                    </div>
                    <div>
                      <div className="font-display text-[14px] font-medium text-ink">{scene.title}</div>
                      <div className="font-mono text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
                        {scene.at}
                      </div>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {scene.visualType}
                  </Badge>
                </div>
                <p className="text-[13px] leading-relaxed text-muted-foreground">
                  {scene.excerpt}
                </p>
                <div className="grid gap-2 rounded-lg bg-muted/20 p-3 text-[11.5px] leading-relaxed sm:grid-cols-2">
                  <div>
                    <span className="font-semibold text-ink">Enseña: </span>
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
                    <span className="font-semibold text-ink">Razón visual: </span>
                    <span className="text-muted-foreground">{scene.visualRationale}</span>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      <Card className="mb-6 flex-row items-start gap-3.5 border-accent bg-primary/8 p-4.5">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <div className="mb-1 text-[13.5px] font-semibold text-ink">
            {selectedSegment ? 'Configuración de Reutilización Lista' : 'Generación Híbrida Inteligente'}
          </div>
          <p className="text-[13px] leading-relaxed">
            {selectedSegment 
              ? 'Has seleccionado reutilizar un video existente. Haz clic en "Confirmar y Volver" para aplicar este asset.'
              : 'Revisa el guion y el storyboard. Puedes iniciar la renderización de audio premium WaveNet e imágenes/capturas animadas desde aquí, o guardar la propuesta aprobada.'}
          </p>
        </div>
      </Card>

      <div className="flex items-center justify-end gap-3">
        <Button variant="outline" onClick={() => setIsEditing((value) => !value)}>
          <SquarePen /> {isEditing ? 'Listo' : 'Editar guion'}
        </Button>
        <Button
          variant="outline"
          onClick={async () => {
            setIsEditing(false)
            if (!route || !hasValidRenderTarget) {
              toast.warning('Este render target sigue siendo local. Abre un módulo persistido para regenerar el storyboard real.')
              return
            }
            await loadStoryboard(true)
          }}
        >
          <RefreshCcw /> Regenerar
        </Button>

        {selectedSegment ? (
          <Button onClick={approve} className="bg-success text-success-foreground hover:bg-success/90">
            <Check /> Confirmar y Volver
          </Button>
        ) : renderingState === 'idle' ? (
          <Button onClick={startRender} disabled={storyboardLoading || !canRenderCurrentStoryboard} className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Film /> {storyboardLoading ? 'Cargando guion KB…' : canRenderCurrentStoryboard ? 'Renderizar Video' : 'Requiere storyboard real'}
          </Button>
        ) : (
          <Button onClick={approve} disabled={renderingState === 'rendering'}>
            <Check /> Guardar y Volver <ArrowRight />
          </Button>
        )}
      </div>
    </div>
  )
}
