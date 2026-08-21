'use client'

import { useEffect, useId, useMemo, useRef, useState } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BookOpen, Check, Download, ExternalLink, Loader2, MoreHorizontal, Sparkles, X } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { LessonContent } from '@/shared/lib/types'
import { api } from '@/shared/lib/api'
import { useStore } from '@/shared/store'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { GroundingBadge } from './GroundingBadge'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { getLessonMarkdown } from './lessonMarkdown'

const markdownComponents: Components = {
  h2: ({ children, ...props }) => <h2 className="lesson-heading" id={slugify(String(children))} {...props}>{children}</h2>,
  h3: ({ children, ...props }) => <h3 className="lesson-subheading" id={String(children).toLowerCase().includes('glosario') ? 'lesson-glossary' : undefined} {...props}>{children}</h3>,
  p: ({ children, ...props }) => <p className="lesson-paragraph" {...props}>{children}</p>,
  ul: ({ children, ...props }) => <ul className="lesson-list" {...props}>{children}</ul>,
  ol: ({ children, ...props }) => <ol className="lesson-list lesson-list-ordered" {...props}>{children}</ol>,
  blockquote: ({ children, ...props }) => <blockquote className="lesson-callout lesson-callout-concept" {...props}>{children}</blockquote>,
  a: ({ children, ...props }) => <a target="_blank" rel="noreferrer" {...props}>{children}</a>,
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children, ...props }) => {
    const language = /language-([\w-]+)/.exec(className ?? '')?.[1]
    const source = String(children).replace(/\n$/, '')

    if (language === 'mermaid') return <MermaidDiagram source={source} />

    // Las lecciones son para personas no técnicas: nunca mostramos código.
    // Los bloques de código se ocultan por completo y el código en línea se
    // degrada a texto plano (sin estilo monoespaciado) para no romper la frase.
    if (language) return null

    return <span {...props}>{children}</span>
  },
}

/** Entrecomilla las etiquetas de nodos Mermaid ([] y {}) para que rendericen
 *  aunque contengan paréntesis, comas o acentos (causa común de parse errors). */
function sanitizeMermaid(source: string): string {
  const wrap = (open: string, close: string, text: string) =>
    text.replace(new RegExp(`\\${open}([^\\${open}\\${close}]*)\\${close}`, 'g'), (match, inner: string) => {
      const trimmed = inner.trim()
      if (!trimmed || (trimmed.startsWith('"') && trimmed.endsWith('"'))) return match
      return `${open}"${trimmed.replace(/"/g, "'")}"${close}`
    })
  return wrap('{', '}', wrap('[', ']', source))
}

/** Lesson: documento editorial Markdown con visuales didácticos y acciones discretas. */
export function LessonView({
  lesson,
  className,
  routeId,
  moduleId,
  editing = false,
  onSave,
  onCancelEdit,
}: {
  lesson: LessonContent
  className?: string
  routeId?: string
  moduleId?: string
  editing?: boolean
  onSave?: (lesson: LessonContent) => Promise<void>
  onCancelEdit?: () => void
}) {
  const [generating, setGenerating] = useState(false)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState<LessonContent>(() => cloneLesson(lesson))
  const { fetchRoutes } = useStore()
  const markdown = useMemo(() => getLessonMarkdown(lesson), [lesson])
  const hasLesson = lesson.sections.length > 0 || Boolean(lesson.markdown?.trim())

  useEffect(() => {
    if (editing) setDraft(cloneLesson(lesson))
  }, [editing, lesson])

  const handleGenerate = async () => {
    if (!routeId || !moduleId) return
    setGenerating(true)
    const toastId = toast.loading(hasLesson ? 'Regenerando Lección…' : 'Creando Lección…', {
      description: 'Generando contenido estructurado y visual.',
    })
    try {
      await api.request(`/learning-paths/${routeId}/modules/${moduleId}/lesson/regenerate`, { method: 'POST', body: JSON.stringify({}) })
      await fetchRoutes()
      toast.success('Lección generada con éxito', { id: toastId })
    } catch (error) {
      toast.error('Error al generar la Lección', { id: toastId, description: error instanceof Error ? error.message : 'Error desconocido' })
    } finally {
      setGenerating(false)
    }
  }

  const triggerDownload = async (url: string, filename: string, type: string) => {
    setDownloading(type)
    const toastId = toast.loading(`Preparando descarga de ${type.toUpperCase()}…`)
    try {
      const response = await fetch(url)
      if (!response.ok) throw new Error('No se pudo descargar el archivo')
      const blobUrl = window.URL.createObjectURL(await response.blob())
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
      toast.success(`${type.toUpperCase()} descargado con éxito`, { id: toastId })
    } catch (error) {
      toast.error(`Error al descargar ${type.toUpperCase()}`, { id: toastId })
      window.open(url, '_blank')
    } finally {
      setDownloading(null)
    }
  }

  if (!hasLesson) {
    return (
      <div className={cn('flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-input bg-card p-10 text-center', className)}>
        <div className="max-w-md"><h4 className="font-display text-base font-semibold text-ink">Este módulo no tiene una Lección generada</h4><p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">Genera una lección didáctica estructurada y visual basada en el tema del módulo y la base de conocimiento.</p></div>
        <Button onClick={handleGenerate} disabled={generating} size="sm">{generating ? <><Loader2 className="size-3.5 animate-spin" /> Generando…</> : <><Sparkles className="size-3.5" /> Generar Lección</>}</Button>
      </div>
    )
  }

  if (editing) return <LessonEditor draft={draft} setDraft={setDraft} saving={saving} setSaving={setSaving} onSave={onSave} onCancelEdit={onCancelEdit} className={className} />

  const headings = lesson.sections.map((section) => section.heading)

  return (
    <div className={cn('lesson-layout', className)}>
      <aside className="lesson-toc" aria-label="Contenido de la lección">
        <span className="lesson-kicker">En esta lección</span>
        <ol>{headings.map((heading, index) => <li className={index === 0 ? 'is-active' : undefined} key={`${heading}-${index}`}><a href={`#${slugify(heading)}`}>{heading}</a></li>)}{lesson.terms.length > 0 && <li><a href="#lesson-glossary">Glosario</a></li>}</ol>
      </aside>

      <article className="lesson-article">
        <header className="lesson-article-header">
          <span className="lesson-eyebrow"><BookOpen className="size-3.5" /> Lesson · Módulo</span>
          <h1>Lección de estudio</h1>
          <p className="lesson-dek">Una lectura guiada para entender los conceptos clave, conectarlos y llevarlos a la práctica.</p>
          <div className="lesson-meta"><GroundingBadge status={lesson.groundingStatus} /><span>Lectura guiada</span><span>{headings.length} secciones</span></div>
        </header>
        <div className="lesson-rule" />
        <div className="lesson-prose"><ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{markdown}</ReactMarkdown></div>
      </article>

      <aside className="lesson-rail">
        <div className="lesson-rail-card"><span className="lesson-kicker">Progreso</span><strong>{headings.length} <small>/ {headings.length} secciones</small></strong><div className="lesson-progress"><span /></div><p>Contenido listo para revisión humana.</p></div>
        <div className="lesson-rail-card"><span className="lesson-kicker">Origen</span><p>{lesson.groundingStatus === 'kb-grounded' ? 'Anclado a documentos aprobados de la Knowledge Base.' : 'Generado desde el objetivo pedagógico del Módulo.'}</p></div>
      </aside>

      <details className="lesson-actions">
        <summary><MoreHorizontal className="size-4" /> Acciones</summary>
        <div className="lesson-action-menu">
          {lesson.pdfUrl ? <button type="button" onClick={() => triggerDownload(lesson.pdfUrl!, `Leccion_${moduleId}.pdf`, 'pdf')} disabled={downloading !== null}><Download /> Descargar PDF</button> : <button type="button" disabled><Download /> PDF no disponible</button>}
          {lesson.txtUrl ? <button type="button" onClick={() => triggerDownload(lesson.txtUrl!, `Leccion_${moduleId}.txt`, 'txt')} disabled={downloading !== null}><Download /> Descargar TXT</button> : <button type="button" disabled><Download /> TXT no disponible</button>}
          <button type="button" onClick={() => window.open(lesson.pdfUrl ?? lesson.txtUrl ?? '#', '_blank')}><ExternalLink /> Abrir artefacto</button>
        </div>
      </details>
    </div>
  )
}

function LessonEditor({ draft, setDraft, saving, setSaving, onSave, onCancelEdit, className }: { draft: LessonContent; setDraft: (value: LessonContent) => void; saving: boolean; setSaving: (value: boolean) => void; onSave?: (lesson: LessonContent) => Promise<void>; onCancelEdit?: () => void; className?: string }) {
  return <div className={cn('rounded-2xl border border-border bg-card p-5', className)}><div className="mb-4"><span className="lesson-kicker">Edición manual</span><p className="mt-1 text-sm text-muted-foreground">Edita el contenido base de la Lección y conserva la estructura Markdown al renderizar.</p></div><div className="space-y-4">{draft.sections.map((section, index) => <div className="rounded-xl border border-border bg-background p-4" key={`${section.heading}-${index}`}><Input value={section.heading} onChange={(event) => setDraft({ ...draft, sections: draft.sections.map((item, itemIndex) => itemIndex === index ? { ...item, heading: event.target.value } : item) })} /><Textarea className="mt-3 resize-y" rows={7} value={section.body} onChange={(event) => setDraft({ ...draft, sections: draft.sections.map((item, itemIndex) => itemIndex === index ? { ...item, body: event.target.value } : item) })} /></div>)}</div><div className="mt-5 flex gap-2"><Button size="sm" onClick={async () => { if (!onSave) return; setSaving(true); try { await onSave(draft) } finally { setSaving(false) } }} disabled={saving}>{saving ? <><Loader2 className="size-3.5 animate-spin" /> Guardando…</> : <><Check className="size-3.5" /> Guardar cambios</>}</Button><Button size="sm" variant="outline" onClick={onCancelEdit} disabled={saving}><X className="size-3.5" /> Cancelar</Button></div></div>
}

function MermaidDiagram({ source }: { source: string }) {
  const diagramRef = useRef<HTMLDivElement>(null)
  const reactId = useId()
  const renderId = `lesson-mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, '')}`
  const [svg, setSvg] = useState('')
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setSvg('')
    setError(false)

    import('mermaid')
      .then(async ({ default: mermaid }) => {
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'base',
          themeVariables: {
            primaryColor: '#eeeafd',
            primaryTextColor: '#1d1b25',
            primaryBorderColor: '#6847c7',
            lineColor: '#756f82',
            secondaryColor: '#eaf5c8',
            tertiaryColor: '#fbe8db',
          },
        })
        try {
          const result = await mermaid.render(renderId, sanitizeMermaid(source))
          if (cancelled) return
          setSvg(result.svg)
          requestAnimationFrame(() => result.bindFunctions?.(diagramRef.current!))
        } catch {
          if (!cancelled) setError(true)
        }
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })

    return () => {
      cancelled = true
    }
  }, [renderId, source])

  // Nunca exponemos el código del diagrama a una audiencia no técnica: si falla,
  // el diagrama es opcional, así que lo omitimos por completo.
  if (error) return null

  return <figure className="lesson-diagram lesson-mermaid" ref={diagramRef} aria-label="Diagrama de la lección">{svg ? <div dangerouslySetInnerHTML={{ __html: svg }} /> : <figcaption>Preparando diagrama…</figcaption>}</figure>
}

function slugify(value: string): string {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

function cloneLesson(lesson: LessonContent): LessonContent {
  return { ...lesson, sections: lesson.sections.map((section) => ({ ...section })), terms: lesson.terms.map((term) => ({ ...term })) }
}
