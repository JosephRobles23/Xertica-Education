import { useMemo, useState } from 'react'
import { BookOpen, Check, Copy, Download, FileDown, FileText } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import type { LabContent } from '@/shared/lib/types'

export function LabView({ lab, className }: { lab: LabContent; className?: string }) {
  const [copied, setCopied] = useState(false)
  const classroomText = useMemo(() => lab.classroomText || buildClassroomText(lab), [lab])

  const copyText = async () => {
    await navigator.clipboard.writeText(classroomText)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
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

        <pre className="max-h-[560px] overflow-auto whitespace-pre-wrap px-4 py-4 font-sans text-[14px] leading-relaxed text-foreground">
          {classroomText}
        </pre>
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
