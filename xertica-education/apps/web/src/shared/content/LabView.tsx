'use client'

import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Check, Copy, Download, FileDown, FileText, Loader2, X } from 'lucide-react'
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
  const [draft, setDraft] = useState<LabContent>(() => cloneLab(lab))
  const classroomText = useMemo(() => lab.classroomText || buildClassroomText(lab), [lab])
  const sections = useMemo(() => parseLabSections(classroomText), [classroomText])

  useEffect(() => {
    if (!editing) return
    setDraft(cloneLab(lab))
  }, [editing, lab])

  const copyText = async () => {
    await navigator.clipboard.writeText(classroomText)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  if (editing) {
    const editableText = draft.classroomText || buildClassroomText(draft)
    return (
      <div className={cn('grid grid-cols-1 gap-6 md:grid-cols-3', className)}>
        <div className="flex flex-col gap-4 md:col-span-2">
          <div className="rounded-xl border-[1.5px] bg-card p-4.5">
            <div className="mb-3 flex items-center gap-2">
              <FileText className="size-4 text-primary" />
              <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                Texto editable
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
              <Textarea
                rows={18}
                value={editableText}
                onChange={(event) =>
                  setDraft((prev) => ({
                    ...prev,
                    classroomText: event.target.value,
                  }))
                }
                placeholder="Texto del laboratorio listo para Classroom"
                className="resize-y"
              />
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border-[1.5px] border-accent bg-primary/6 p-4.5 shadow-(--shadow-soft)">
            <div className="mb-2 text-[13px] font-semibold text-ink">Edición manual</div>
            <p className="text-[11.5px] leading-snug text-muted-foreground">
              Ajusta directamente el texto final que luego copiarás o descargarás para Google Classroom.
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
          <Button type="button" size="sm" variant="outline" asChild className="gap-2">
            <a href={lab.txtUrl} target="_blank" rel="noreferrer">
              <Download className="size-4" />
              TXT
            </a>
          </Button>
        ) : null}

        {lab.pdfUrl ? (
          <Button type="button" size="sm" variant="outline" asChild className="gap-2">
            <a href={lab.pdfUrl} target="_blank" rel="noreferrer">
              <FileDown className="size-4" />
              PDF
            </a>
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

    const headingMatch = rawLine.match(/^#{1,6}\s+(.*)$/)
    if (headingMatch) {
      pushCurrent()
      current.title = headingMatch[1]?.trim() || ''
      continue
    }

    if (/^\d+\.\s+/.test(rawLine) && current.title) {
      current.paragraphs.push(rawLine)
      continue
    }

    if (/^[-*]\s+/.test(rawLine)) {
      current.bullets.push(rawLine.replace(/^[-*]\s+/, ''))
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
