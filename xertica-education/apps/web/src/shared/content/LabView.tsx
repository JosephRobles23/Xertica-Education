'use client'

import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Check, Copy, Download, FileDown, FileText, Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import type { LabContent } from '@/shared/lib/types'

export function LabView({
  lab,
  className,
  editing = false,
  onSave,
  onCancelEdit,
}: {
  lab: LabContent
  className?: string
  editing?: boolean
  onSave?: (lab: LabContent) => Promise<void>
  onCancelEdit?: () => void
}) {
  const [copied, setCopied] = useState(false)
  const [saving, setSaving] = useState(false)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [draft, setDraft] = useState<LabContent>(() => editableLab(lab))
  const [editableSections, setEditableSections] = useState<EditableLabSection[]>(() =>
    editableSectionsFromText(editableLab(lab).classroomText || buildClassroomText(lab)),
  )
  const classroomText = useMemo(() => lab.classroomText || buildClassroomText(lab), [lab])
  const sections = useMemo(() => parseLabSections(classroomText), [classroomText])

  useEffect(() => {
    if (!editing) return
    const nextDraft = editableLab(lab)
    setDraft(nextDraft)
    setEditableSections(editableSectionsFromText(nextDraft.classroomText || buildClassroomText(nextDraft)))
  }, [editing, lab])

  const copyText = async () => {
    await navigator.clipboard.writeText(classroomText)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  const triggerDownload = async (url: string, filename: string, type: string) => {
    setDownloading(type)
    const toastId = toast.loading(`Preparando descarga de ${type.toUpperCase()}...`)
    try {
      const response = await fetch(url)
      if (!response.ok) throw new Error('Network response was not ok')
      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(blobUrl)
      toast.success(`${type.toUpperCase()} descargado con éxito`, { id: toastId })
    } catch (error) {
      console.error(error)
      toast.error(`No se pudo descargar ${type.toUpperCase()}`, { id: toastId })
    } finally {
      setDownloading(null)
    }
  }

  if (editing) {
    const editableText = serializeEditableSections(editableSections)
    return (
      <div className={cn('grid grid-cols-1 gap-6 md:grid-cols-3', className)}>
        <div className="flex flex-col gap-4 md:col-span-2">
          <div className="rounded-xl border-[1.5px] bg-card p-4.5">
            <div className="mb-3 flex items-center gap-2">
              <FileText className="size-4 text-primary" />
              <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                Bloques editables
              </span>
            </div>
            <div className="space-y-3">
              <Input
                value={draft.title || ''}
                onChange={(event) =>
                  setDraft((prev) => ({
                    ...prev,
                    title: event.target.value,
                  }))
                }
                placeholder="Título del laboratorio"
              />

              <div className="flex max-h-[680px] flex-col gap-3 overflow-y-auto pr-1">
                {editableSections.map((section, index) => (
                  <div key={section.id} className="rounded-xl border-[1.5px] border-secondary bg-background/70 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <span className="font-mono text-[10px] font-semibold text-primary">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                        Bloque editable
                      </span>
                    </div>
                    <div className="space-y-3">
                      <Input
                        value={section.title}
                        onChange={(event) =>
                          setEditableSections((prev) =>
                            prev.map((item) =>
                              item.id === section.id ? { ...item, title: event.target.value } : item,
                            ),
                          )
                        }
                        placeholder="Título del bloque"
                      />
                      <Textarea
                        rows={Math.max(4, Math.min(10, section.body.split('\n').length + 2))}
                        value={section.body}
                        onChange={(event) =>
                          setEditableSections((prev) =>
                            prev.map((item) =>
                              item.id === section.id ? { ...item, body: event.target.value } : item,
                            ),
                          )
                        }
                        placeholder="Contenido del bloque"
                        className="resize-y"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border-[1.5px] border-accent bg-primary/6 p-4.5 shadow-(--shadow-soft)">
            <div className="mb-2 text-[13px] font-semibold text-ink">Edición manual</div>
            <p className="text-[11.5px] leading-snug text-muted-foreground">
              Ajusta cada bloque del laboratorio. Al guardar, se actualizan el texto y el PDF sin regenerar con IA.
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <Button
                size="sm"
                onClick={async () => {
                  if (!onSave) return
                  setSaving(true)
                  try {
                    await onSave({
                      ...draft,
                      classroomText: editableText,
                    })
                  } finally {
                    setSaving(false)
                  }
                }}
                disabled={saving}
              >
                {saving ? (
                  <>
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Guardando...
                  </>
                ) : (
                  <>
                    <Check /> Guardar cambios
                  </>
                )}
              </Button>
              <Button size="sm" variant="outline" onClick={onCancelEdit} disabled={saving}>
                <X /> Cancelar
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <BookOpen className="size-4 text-primary" />
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          Texto para Google Classroom
        </span>
        {lab.estimatedTimeMinutes ? (
          <span className="ml-auto rounded-full bg-secondary px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
            {lab.estimatedTimeMinutes} min
          </span>
        ) : null}
      </div>

      <div className="rounded-xl border border-border bg-card">
        <div className="flex flex-wrap items-center gap-2 border-b border-secondary px-4 py-3">
          <FileText className="size-4 text-primary" />
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-[15px] font-semibold text-ink">
              {lab.title || 'Laboratorio práctico'}
            </h3>
            {lab.tools && lab.tools.length > 0 ? (
              <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
                {lab.tools.map((tool) => tool.name).join(' · ')}
              </p>
            ) : null}
          </div>
        </div>

        <div className="flex max-h-[560px] flex-col gap-4 overflow-auto px-4 py-4">
          {sections.map((section, index) => (
            <div key={`${section.title}-${index}`} className="rounded-xl border-[1.5px] border-secondary bg-background/70 p-4">
              {section.title ? (
                <div className="mb-2 text-[14px] font-semibold text-ink">
                  {section.title}
                </div>
              ) : null}

              <div className="space-y-2 text-[13.5px] leading-relaxed text-foreground">
                {section.paragraphs.map((paragraph, paragraphIndex) => (
                  <p key={`${paragraph}-${paragraphIndex}`}>{renderInlineMarkdown(paragraph)}</p>
                ))}
                {section.bullets.length > 0 && (
                  <ul className="space-y-1.5 pl-5 text-[13px] text-muted-foreground">
                    {section.bullets.map((bullet, bulletIndex) => (
                      <li key={`${bullet}-${bulletIndex}`} className="list-disc">
                        {renderInlineMarkdown(bullet)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" onClick={copyText} className="gap-2">
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
          {copied ? 'Copiado' : 'Copiar texto'}
        </Button>

        {lab.txtUrl ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => triggerDownload(lab.txtUrl!, `Laboratorio_${lab.title || 'practico'}.txt`, 'txt')}
            disabled={downloading !== null}
            className="gap-2"
          >
            {downloading === 'txt' ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
            TXT
          </Button>
        ) : null}

        {lab.pdfUrl ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => triggerDownload(lab.pdfUrl!, `Laboratorio_${lab.title || 'practico'}.pdf`, 'pdf')}
            disabled={downloading !== null}
            className="gap-2"
          >
            {downloading === 'pdf' ? <Loader2 className="size-4 animate-spin" /> : <FileDown className="size-4" />}
            PDF
          </Button>
        ) : null}
      </div>
    </div>
  )
}

function buildClassroomText(lab: LabContent) {
  const lines: string[] = []
  lines.push(`Laboratorio: ${lab.title || 'Práctica guiada'}`)
  if (lab.estimatedTimeMinutes) lines.push(`Tiempo estimado: ${lab.estimatedTimeMinutes} minutos`)
  if (lab.objective) lines.push('', lab.objective)
  if (lab.scenario) lines.push('', lab.scenario)

  const tools = lab.tools?.map((tool) => tool.name).filter(Boolean)
  if (tools?.length) lines.push('', `Herramienta principal: ${tools.join(' · ')}`)

  const instructions =
    lab.instructions && lab.instructions.length > 0
      ? lab.instructions
      : lab.steps.map((step, index) => ({
          step: index + 1,
          title: step.title,
          description: step.desc,
          expectedResult: undefined,
          tip: step.tip,
        }))

  lines.push('', '1. Desafío')
  lines.push('Aterriza el caso: define qué vas a crear, resolver o decidir usando el contenido del módulo.')

  instructions.forEach((instruction) => {
    lines.push('', `${instruction.step + 1}. ${instruction.title}`)
    lines.push(instruction.description)
    if (instruction.expectedResult) lines.push(`Resultado esperado: ${instruction.expectedResult}`)
  })

  if (lab.deliverable) {
    lines.push('', 'Entrega')
    lines.push(lab.deliverable.description)
    lines.push(`Formato: ${lab.deliverable.format}`)
    if (lab.deliverable.successCriteria.length > 0) {
      lines.push('Debe mostrar:')
      lab.deliverable.successCriteria.forEach((criterion) => lines.push(`- ${criterion}`))
    }
  }

  const tips = instructions.map((instruction) => instruction.tip).filter(Boolean).slice(0, 2)
  if (tips.length > 0) {
    lines.push('', 'Tips de oro')
    tips.forEach((tip) => lines.push(`- ${tip}`))
  }

  if (lab.safetyNotes?.[0]) lines.push('', `Nota clave: ${lab.safetyNotes[0]}`)
  if (lab.reflectionQuestions && lab.reflectionQuestions.length > 0) {
    lines.push('', 'Cierre rápido')
    lab.reflectionQuestions.forEach((question) => lines.push(`- ${question}`))
  }

  return lines.join('\n')
}

interface EditableLabSection {
  id: string
  title: string
  body: string
}

function editableLab(lab: LabContent): LabContent {
  const draft = cloneLab(lab)
  draft.classroomText = markdownToEditableText(draft.classroomText || buildClassroomText(draft))
  return draft
}

function editableSectionsFromText(text: string): EditableLabSection[] {
  const cleanText = markdownToEditableText(text)
  const parsed = parseLabSections(cleanText)
  const sections = parsed.map((section, index) => ({
    id: `section-${index}`,
    title: section.title || `Bloque ${index + 1}`,
    body: [...section.paragraphs, ...section.bullets.map((bullet) => `• ${bullet}`)].join('\n'),
  }))

  return sections.length > 0
    ? sections
    : [{ id: 'section-0', title: 'Resumen del laboratorio', body: cleanText }]
}

function serializeEditableSections(sections: EditableLabSection[]) {
  return sections
    .map((section) => [section.title.trim(), section.body.trim()].filter(Boolean).join('\n'))
    .filter(Boolean)
    .join('\n\n')
}

function markdownToEditableLine(text: string) {
  return markdownToEditableText(text).replace(/\n+/g, ' ').trim()
}

function markdownToEditableText(text: string) {
  return text
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line) => {
      let next = line.trimEnd()
      next = next.replace(/^#{1,6}\s+/, '')
      next = next.replace(/^>\s?/, '')
      next = next.replace(/^[-*]\s+/, '• ')
      next = next.replace(/^\s{0,3}\d+\.\s+/, (match) => match.trimStart())
      next = next.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1 ($2)')
      next = next.replace(/\*\*\*([^*]+)\*\*\*/g, '$1')
      next = next.replace(/\*\*([^*]+)\*\*/g, '$1')
      next = next.replace(/__([^_]+)__/g, '$1')
      next = next.replace(/`([^`]+)`/g, '$1')
      return next
    })
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function cloneLab(lab: LabContent): LabContent {
  return {
    ...lab,
    tools: lab.tools?.map((tool) => ({ ...tool })),
    prerequisites: lab.prerequisites ? [...lab.prerequisites] : undefined,
    instructions: lab.instructions?.map((instruction) => ({ ...instruction })),
    deliverable: lab.deliverable
      ? {
          ...lab.deliverable,
          successCriteria: [...lab.deliverable.successCriteria],
        }
      : undefined,
    reflectionQuestions: lab.reflectionQuestions ? [...lab.reflectionQuestions] : undefined,
    sourceReferences: lab.sourceReferences?.map((source) => ({ ...source })),
    safetyNotes: lab.safetyNotes ? [...lab.safetyNotes] : undefined,
    steps: (lab.steps ?? []).map((step) => ({ ...step })),
    console: [...(lab.console ?? [])],
  }
}

function parseLabSections(text: string) {
  const lines = text
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line) => line.trim())

  const sections: Array<{ title?: string; paragraphs: string[]; bullets: string[] }> = []
  let current = { title: '', paragraphs: [] as string[], bullets: [] as string[] }

  const pushCurrent = () => {
    if (!current.title && current.paragraphs.length === 0 && current.bullets.length === 0) return
    sections.push({
      title: current.title || undefined,
      paragraphs: [...current.paragraphs],
      bullets: [...current.bullets],
    })
    current = { title: '', paragraphs: [], bullets: [] }
  }

  for (const rawLine of lines) {
    if (!rawLine) continue

    const heading = extractLabHeading(rawLine)
    if (heading) {
      pushCurrent()
      current.title = heading
      continue
    }

    if (/^[-*•]\s+/.test(rawLine)) {
      current.bullets.push(rawLine.replace(/^[-*•]\s+/, ''))
      continue
    }

    if (!current.title && sections.length === 0) {
      current.title = 'Resumen del laboratorio'
    }

    current.paragraphs.push(rawLine)
  }

  pushCurrent()

  return sections.length > 0
    ? sections
    : [{ title: 'Resumen del laboratorio', paragraphs: [text], bullets: [] }]
}

function extractLabHeading(line: string) {
  const trimmed = line.trim()
  const markdownHeading = trimmed.match(/^#{1,6}\s+(.*)$/)
  if (markdownHeading?.[1]) return markdownHeading[1].trim()

  const boldHeading = trimmed.match(/^\*\*\s*(\d+\.\s+[^*]+|[^*]{1,70})\s*\*\*:?$/)
  if (boldHeading?.[1]) return boldHeading[1].trim()

  const numberedStep = trimmed.match(/^(\d+\.\s+.{1,70})$/)
  if (numberedStep?.[1]) return numberedStep[1].trim()

  const clean = markdownToEditableLine(trimmed).replace(/:$/, '')
  const knownHeadings = new Set([
    'Resumen del laboratorio',
    'Tu Desafío',
    'Tu Desafio',
    'Tu Misión',
    'Tu Mision',
    'Manos a la obra',
    'Pasos a Seguir',
    'Pasos a seguir',
    'Entrega',
    'Entregable',
    'Tu Entregable',
    'Criterios de éxito',
    'Criterios de exito',
    'Tips Pro',
    'Tips Rápidos',
    'Tips Rapidos',
    'Tips de oro',
    'Cierre rápido',
    'Cierre rapido',
  ])
  if (knownHeadings.has(clean)) return clean

  return null
}

function renderInlineMarkdown(text: string) {
  const parts = text.replace(/\*\*\*/g, '**').split('**')
  return parts.map((part, index) =>
    index % 2 === 1 ? (
      <strong key={`${part}-${index}`} className="font-semibold text-ink">
        {part}
      </strong>
    ) : (
      part
    ),
  )
}
