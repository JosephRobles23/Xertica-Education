/**
 * Domain model — Xertica Education Studio.
 * Estados imposibles = irrepresentables: todo estado de contenido vive en
 * `ContentStatus`, y cada tipo de contenido tiene su forma exacta.
 */

export const CONTENT_KINDS = ['lesson', 'video', 'infografia', 'quiz', 'lab'] as const
export type ContentKind = (typeof CONTENT_KINDS)[number]

export const KIND_LABEL: Record<ContentKind, string> = {
  lesson: 'Lesson',
  video: 'Video',
  infografia: 'Infografía',
  quiz: 'Quiz',
  lab: 'Laboratorio',
}

export type ContentStatus = 'borrador' | 'generado' | 'en-revision' | 'aprobado'

export const STATUS_LABEL: Record<ContentStatus, string> = {
  borrador: 'borrador',
  generado: 'generado',
  'en-revision': 'en revisión',
  aprobado: 'aprobado',
}

/* ── Content shapes ─────────────────────────────────────────────── */

export interface LessonSection {
  heading: string
  body: string
}

export interface LessonContent {
  sections: readonly LessonSection[]
  terms: readonly { term: string; def: string }[]
}

export interface VideoSegment {
  at: string
  label: string
}

/** El fotograma: portada 16:9 del video renderizado con Veo. */
export interface VideoContent {
  duration: string
  caption: string
  /** Clases tailwind del gradiente de la escena del fotograma. */
  gradient: string
  emoji: string
  segments: readonly VideoSegment[]
}

export type AspectRatio = 'vertical' | 'horizontal' | 'square' | 'auto'

export interface InfografiaContent {
  title: string
  bullets: readonly string[]
  footer: readonly [string, string]
  imageUrl?: string
  pdfUrl?: string
  aspectRatio?: AspectRatio
}

export interface QuizQuestion {
  q: string
  opts: readonly [string, string, string]
  correct: 0 | 1 | 2
}

export interface QuizContent {
  questions: readonly QuizQuestion[]
}

export interface LabStep {
  title: string
  desc: string
  tool?: string
  tip?: string
}

export interface LabContent {
  steps: readonly LabStep[]
  console: readonly string[]
}

/** Pack de contenido de una ruta: alimenta previews y el asset final. */
export interface ContentPack {
  lesson: LessonContent
  video: VideoContent
  infografia: InfografiaContent
  quiz: QuizContent
  lab: LabContent
}

/* ── Módulos y rutas ────────────────────────────────────────────── */

export interface ModuleContentRef {
  kind: ContentKind
  status: ContentStatus
  summary: string
}

export interface RouteModule {
  id: string
  num: string
  name: string
  type: string
  status: ContentStatus
  contents: readonly ModuleContentRef[]
}

export interface SourceVideoPreview {
  channel: string
  duration: string
  gradient: string
  emoji: string
  /** Cuando existe, se embebe el reproductor real de YouTube en vez del placeholder. */
  youtubeId?: string
  videoTitle?: string
}

export interface Source {
  title: string
  plat: string
  verified: boolean
  quote: string
  url?: string
  kind?: 'youtube' | 'documentation' | 'article'
  toolName?: string
  vendor?: string
  verificationReason?: string
  relevanceScore?: number
  suggestedUse?: 'lesson' | 'video' | 'lab' | 'quiz' | 'general'
  status?: 'approved' | 'requires-review' | 'rejected'
  videoPreview?: SourceVideoPreview
  metadata?: Record<string, unknown>
}

export type CustomerArea = 'RRHH' | 'Finanzas' | 'TI' | 'Educacion' | 'Salud' | 'General'
export type GoogleWorkspaceUsage = 'yes' | 'no' | 'unknown'

export interface CustomerContext {
  url?: string
  industry?: string
  area?: CustomerArea
  usesGoogleWorkspace?: GoogleWorkspaceUsage
  audienceLevel?: string
  baseMaterialFile?: {
    name: string
    type: string
    sizeKb: number
  }
  inferredFrom?: readonly ('url' | 'brief' | 'material')[]
  companyName?: string
}

export type RouteId = '01' | '02' | '03' | '04' | '05' | '06' | '07'

export interface LearningRoute {
  id: RouteId
  name: string
  status: ContentStatus
  objective: string
  customerContext?: CustomerContext
  sources: readonly Source[]
  pack: ContentPack
  modules: readonly RouteModule[]
}

/* ── Estructura propuesta (Gate 0) ──────────────────────────────── */

export interface ProposalModule {
  id: string
  title: string
  desc: string
  min: number
  comps: Record<ContentKind, boolean>
  alt: { title: string; desc: string }
  type?: string
}
