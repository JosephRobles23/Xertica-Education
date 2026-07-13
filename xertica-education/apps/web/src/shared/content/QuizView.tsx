'use client'

import { useEffect, useState } from 'react'
import { Check, Download, Loader2, RotateCcw, Sparkles, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { cn } from '@/shared/lib/utils'
import type { QuizContent } from '@/shared/lib/types'
import { api } from '@/shared/lib/api'
import { GroundingBadge } from './GroundingBadge'
import { useStore } from '@/shared/store'

export function QuizView({
  quiz,
  className,
  routeId,
  moduleId,
  editing = false,
  onSave,
  onCancelEdit,
}: {
  quiz: QuizContent
  className?: string
  routeId?: string
  moduleId?: string
  editing?: boolean
  onSave?: (quiz: QuizContent) => Promise<void>
  onCancelEdit?: () => void
}) {
  const [feedback, setFeedback] = useState('')
  const [generating, setGenerating] = useState(false)
  const [downloading, setDownloading] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState<QuizContent>(() => cloneQuiz(quiz))
  const { fetchRoutes } = useStore()

  const hasQuiz = quiz && quiz.questions && quiz.questions.length > 0

  useEffect(() => {
    if (!editing) return
    setDraft(cloneQuiz(quiz))
  }, [editing, quiz])

  const handleGenerate = async () => {
    if (!routeId || !moduleId) return
    setGenerating(true)
    const toastLabel = hasQuiz ? 'Regenerando Quiz con tu feedback…' : 'Creando Quiz por primera vez…'
    const toastId = toast.loading(toastLabel, {
      description: 'Generando el Quiz en PDF y TXT. Esto puede tardar unos segundos.',
    })
    try {
      await api.request(`/learning-paths/${routeId}/modules/${moduleId}/quiz/regenerate`, {
        method: 'POST',
        body: JSON.stringify({
          user_prompt: feedback,
        }),
      })
      await fetchRoutes()
      toast.success('Quiz generado con éxito', { id: toastId })
      setFeedback('')
    } catch (e) {
      console.error(e)
      toast.error('Error al generar el Quiz', {
        id: toastId,
        description: e instanceof Error ? e.message : 'Error desconocido',
      })
    } finally {
      setGenerating(false)
    }
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
    } catch (e) {
      console.error(e)
      toast.error(`Error al descargar ${type.toUpperCase()}. Abriendo en nueva pestaña...`, { id: toastId })
      window.open(url, '_blank')
    } finally {
      setDownloading(null)
    }
  }

  if (!hasQuiz) {
    return (
      <div className={cn('flex flex-col items-center justify-center p-8 border-[1.5px] border-dashed border-input rounded-xl bg-card text-center gap-4', className)}>
        <div className="max-w-md">
          <h4 className="font-display text-[15px] font-medium text-ink mb-1">Este módulo no tiene un Quiz generado</h4>
          <p className="text-[12.5px] text-muted-foreground leading-relaxed">
            Genera un quiz de opción múltiple basado en el nombre y tema del módulo, descargable en PDF y TXT.
          </p>
        </div>
        <Button onClick={handleGenerate} disabled={generating} size="sm">
          {generating ? (
            <>
              <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Generando...
            </>
          ) : (
            <>
              <Sparkles /> Generar Quiz
            </>
          )}
        </Button>
      </div>
    )
  }

  if (editing) {
    return (
      <div className={cn('grid grid-cols-1 gap-6 md:grid-cols-3', className)}>
        <div className="flex max-h-[700px] flex-col gap-4 overflow-y-auto pr-1 md:col-span-2">
          {draft.questions.map((question, questionIndex) => (
            <div key={`${question.q}-${questionIndex}`} className="rounded-xl border-[1.5px] bg-card p-4">
              <div className="mb-3 flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-primary">
                  {String(questionIndex + 1).padStart(2, '0')}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                  Pregunta editable
                </span>
              </div>

              <div className="space-y-3">
                <Textarea
                  rows={3}
                  value={question.q}
                  onChange={(event) =>
                    setDraft((prev) => ({
                      ...prev,
                      questions: prev.questions.map((item, itemIndex) =>
                        itemIndex === questionIndex ? { ...item, q: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder="Texto de la pregunta"
                  className="resize-y"
                />

                <div className="space-y-2">
                  {question.opts.map((option, optionIndex) => {
                    const isCorrect = optionIndex === question.correct
                    return (
                      <div key={`${option}-${optionIndex}`} className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            setDraft((prev) => ({
                              ...prev,
                              questions: prev.questions.map((item, itemIndex) =>
                                itemIndex === questionIndex ? { ...item, correct: optionIndex } : item,
                              ),
                            }))
                          }
                          className={cn(
                            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold transition-colors',
                            isCorrect
                              ? 'border-success bg-success text-success-foreground'
                              : 'border-input bg-background text-muted-foreground hover:border-primary',
                          )}
                        >
                          {String.fromCharCode(65 + optionIndex)}
                        </button>
                        <Input
                          value={option}
                          onChange={(event) =>
                            setDraft((prev) => ({
                              ...prev,
                              questions: prev.questions.map((item, itemIndex) =>
                                itemIndex === questionIndex
                                  ? {
                                      ...item,
                                      opts: item.opts.map((currentOption, currentOptionIndex) =>
                                        currentOptionIndex === optionIndex ? event.target.value : currentOption,
                                      ),
                                    }
                                  : item,
                              ),
                            }))
                          }
                          placeholder={`Opción ${String.fromCharCode(65 + optionIndex)}`}
                        />
                      </div>
                    )
                  })}
                </div>

                <Textarea
                  rows={4}
                  value={question.explanation || ''}
                  onChange={(event) =>
                    setDraft((prev) => ({
                      ...prev,
                      questions: prev.questions.map((item, itemIndex) =>
                        itemIndex === questionIndex ? { ...item, explanation: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder="Explicación de la respuesta correcta"
                  className="resize-y"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border-[1.5px] border-accent bg-primary/6 p-4.5 shadow-(--shadow-soft)">
            <div className="mb-2 text-[13px] font-semibold text-ink">Edición manual</div>
            <p className="text-[11.5px] leading-snug text-muted-foreground">
              Puedes corregir preguntas, opciones y la respuesta correcta sin pedir otra generación.
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <Button
                size="sm"
                onClick={async () => {
                  if (!onSave) return
                  setSaving(true)
                  try {
                    await onSave(draft)
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
    <div className={cn('grid grid-cols-1 md:grid-cols-3 gap-6', className)}>
      {/* Columna Izquierda: Previsualización de Preguntas en Pantalla */}
      <div className="md:col-span-2 flex flex-col gap-4">
        <GroundingBadge status={quiz.groundingStatus} />
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
            Previsualización de Preguntas
          </span>
          <span className="font-mono text-[11px] text-muted-foreground">
            {quiz.questions.length} Preguntas
          </span>
        </div>

        <div className="flex flex-col gap-3 max-h-[500px] overflow-y-auto pr-1">
          {quiz.questions.map((q, qi) => (
            <div key={qi} className="rounded-xl border-[1.5px] bg-card p-4">
              <div className="mb-2.5 flex gap-2">
                <span className="font-mono text-xs font-semibold text-primary">
                  {String(qi + 1).padStart(2, '0')}
                </span>
                <span className="text-[13.5px] font-semibold leading-snug text-ink">{q.q}</span>
              </div>
              <div className="grid grid-cols-1 gap-1.5 pl-5">
                {q.opts.map((opt, oi) => {
                  const isCorrect = oi === q.correct
                  return (
                    <div
                      key={oi}
                      className={cn(
                        'flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[12.5px] border border-transparent',
                        isCorrect
                          ? 'bg-success/8 text-success font-medium border-success/20'
                          : 'text-muted-foreground'
                      )}
                    >
                      <span className={cn(
                        'flex size-4.5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold border',
                        isCorrect
                          ? 'bg-success text-success-foreground border-success'
                          : 'bg-secondary text-muted-foreground border-border'
                      )}>
                        {isCorrect ? <Check className="size-2.5" strokeWidth={3} /> : String.fromCharCode(65 + oi)}
                      </span>
                      <span>{opt}</span>
                    </div>
                  )
                })}
              </div>

              {q.explanation && (
                <div className="mt-3 pl-5 text-[11.5px] text-muted-foreground leading-relaxed border-t border-secondary pt-2">
                  <span className="font-semibold text-ink">Explicación:</span> {q.explanation}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Columna Derecha: Descargas y Regeneración */}
      <div className="flex flex-col gap-4">
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
          Acciones y Descarga
        </span>

        <div className="rounded-xl border-[1.5px] bg-card p-4.5 flex flex-col gap-4 shadow-(--shadow-soft)">
          <div>
            <h4 className="text-[13px] font-semibold text-ink mb-1">Descargar Fichas</h4>
            <p className="text-[11.5px] text-muted-foreground leading-snug">
              Obtén el quiz formateado listo para imprimir o compartir con tus estudiantes.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            {quiz.pdfUrl ? (
              <button
                type="button"
                onClick={() => triggerDownload(quiz.pdfUrl!, `Quiz_${moduleId}.pdf`, 'pdf')}
                disabled={downloading !== null}
                className="flex h-9 w-full items-center justify-center gap-1.5 rounded-md bg-primary/10 font-mono text-[11px] font-semibold text-primary transition-colors hover:bg-primary/20 text-center cursor-pointer disabled:opacity-50"
              >
                <Download className="size-3.5" /> Descargar PDF
              </button>
            ) : (
              <div className="flex h-9 w-full items-center justify-center rounded-md bg-secondary font-mono text-[11px] font-semibold text-muted-foreground opacity-50">
                PDF no disponible
              </div>
            )}

            {quiz.txtUrl ? (
              <button
                type="button"
                onClick={() => triggerDownload(quiz.txtUrl!, `Quiz_${moduleId}.txt`, 'txt')}
                disabled={downloading !== null}
                className="flex h-9 w-full items-center justify-center gap-1.5 rounded-md bg-success/12 font-mono text-[11px] font-semibold text-success transition-colors hover:bg-success/20 text-center cursor-pointer disabled:opacity-50"
              >
                <Download className="size-3.5" /> Descargar TXT
              </button>
            ) : (
              <div className="flex h-9 w-full items-center justify-center rounded-md bg-secondary font-mono text-[11px] font-semibold text-muted-foreground opacity-50">
                TXT no disponible
              </div>
            )}
          </div>
        </div>

        <div className="rounded-xl border-[1.5px] bg-card p-4.5 flex flex-col gap-3.5 shadow-(--shadow-soft)">
          <div className="flex items-center gap-1.5 text-[13px] font-semibold text-ink">
            <Sparkles className="size-4 text-primary" />
            ¿Quieres otras preguntas?
          </div>
          <p className="text-[11.5px] text-muted-foreground leading-snug">
            Describe los temas adicionales o el enfoque que deseas para regenerar el Quiz con nuevas preguntas.
          </p>

          <Textarea
            rows={3}
            placeholder="Ej: Incluye preguntas sobre buenas prácticas y haz énfasis en la diferencia entre listas y tuplas..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            disabled={generating}
            className="text-[11.5px] resize-none"
          />

          <Button
            onClick={handleGenerate}
            disabled={generating || !feedback.trim()}
            size="sm"
            className="w-full text-xs"
          >
            {generating ? (
              <>
                <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Regenerando...
              </>
            ) : (
              <>
                <RotateCcw /> Regenerar con Feedback
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

function cloneQuiz(quiz: QuizContent): QuizContent {
  return {
    ...quiz,
    questions: quiz.questions.map((question) => ({
      ...question,
      opts: [...question.opts],
    })),
  }
}
