'use client'

import { useEffect, useState } from 'react'
import { BookOpen, Check, Download, Loader2, Sparkles, X } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { LessonContent } from '@/shared/lib/types'
import { api } from '@/shared/lib/api'
import { useStore } from '@/shared/store'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'

const renderFormattedText = (text: string) => {
  if (!text) return null
  // Unify *** and ** to **
  const unified = text.replace(/\*\*\*/g, '**')
  const parts = unified.split('**')
  return parts.map((part, index) => {
    if (index % 2 === 1) {
      return (
        <strong key={index} className="font-semibold text-ink">
          {part}
        </strong>
      )
    }
    return part
  })
}

/** Lesson: secciones de texto + glosario de términos clave + descarga de fichas. */
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

  const hasLesson = lesson && lesson.sections && lesson.sections.length > 0

  useEffect(() => {
    if (!editing) return
    setDraft(cloneLesson(lesson))
  }, [editing, lesson])

  const handleGenerate = async () => {
    if (!routeId || !moduleId) return
    setGenerating(true)
    const toastLabel = hasLesson ? 'Regenerando Lección con tu feedback…' : 'Creando Lección por primera vez…'
    const toastId = toast.loading(toastLabel, {
      description: 'Generando el contenido detallado y glosario. Esto puede tardar unos segundos.',
    })
    try {
      await api.request(`/learning-paths/${routeId}/modules/${moduleId}/lesson/regenerate`, {
        method: 'POST',
        body: JSON.stringify({}),
      })
      await fetchRoutes()
      toast.success('Lección generada con éxito', { id: toastId })
    } catch (e) {
      console.error(e)
      toast.error('Error al generar la Lección', {
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

  if (!hasLesson) {
    return (
      <div className={cn('flex flex-col items-center justify-center p-8 border-[1.5px] border-dashed border-input rounded-xl bg-card text-center gap-4', className)}>
        <div className="max-w-md">
          <h4 className="font-display text-[15px] font-medium text-ink mb-1">Este módulo no tiene una Lección generada</h4>
          <p className="text-[12.5px] text-muted-foreground leading-relaxed">
            Genera una lección didáctica estructurada y un glosario de términos clave basados en el tema del módulo y la base de conocimientos.
          </p>
        </div>
        <Button onClick={handleGenerate} disabled={generating} size="sm">
          {generating ? (
            <>
              <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Generando...
            </>
          ) : (
            <>
              <Sparkles /> Generar Lección
            </>
          )}
        </Button>
      </div>
    )
  }

  if (editing) {
    return (
      <div className={cn('grid grid-cols-1 gap-6 md:grid-cols-3', className)}>
        <div className="flex flex-col gap-4 md:col-span-2">
          {draft.sections.map((section, index) => (
            <div key={`${section.heading}-${index}`} className="rounded-xl border-[1.5px] bg-card p-4.5">
              <div className="mb-3 flex items-center gap-2">
                <BookOpen className="size-3.5 text-primary" />
                <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                  Sección {index + 1}
                </span>
              </div>
              <div className="space-y-3">
                <Input
                  value={section.heading}
                  onChange={(event) =>
                    setDraft((prev) => ({
                      ...prev,
                      sections: prev.sections.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, heading: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder="Título de la sección"
                />
                <Textarea
                  rows={8}
                  value={section.body}
                  onChange={(event) =>
                    setDraft((prev) => ({
                      ...prev,
                      sections: prev.sections.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, body: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder="Texto de la sección"
                  className="resize-y"
                />
              </div>
            </div>
          ))}

          {draft.terms.length > 0 && (
            <div>
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
                Términos clave
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {draft.terms.map((term, index) => (
                  <div key={`${term.term}-${index}`} className="rounded-xl border-[1.5px] bg-card p-4">
                    <div className="space-y-3">
                      <Input
                        value={term.term}
                        onChange={(event) =>
                          setDraft((prev) => ({
                            ...prev,
                            terms: prev.terms.map((item, itemIndex) =>
                              itemIndex === index ? { ...item, term: event.target.value } : item,
                            ),
                          }))
                        }
                        placeholder="Término"
                      />
                      <Textarea
                        rows={4}
                        value={term.def}
                        onChange={(event) =>
                          setDraft((prev) => ({
                            ...prev,
                            terms: prev.terms.map((item, itemIndex) =>
                              itemIndex === index ? { ...item, def: event.target.value } : item,
                            ),
                          }))
                        }
                        placeholder="Definición"
                        className="resize-y"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border-[1.5px] border-accent bg-primary/6 p-4.5 shadow-(--shadow-soft)">
            <div className="mb-2 text-[13px] font-semibold text-ink">Edición manual</div>
            <p className="text-[11.5px] leading-snug text-muted-foreground">
              Ajusta el texto directamente y guarda los cambios cuando quede listo para revisión humana.
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
      {/* Columna Izquierda: Secciones y Glosario */}
      <div className="md:col-span-2 flex flex-col gap-4">
        {lesson.sections.map((s) => (
          <div key={s.heading} className="rounded-xl border-[1.5px] bg-card p-4.5">
            <div className="mb-1.5 flex items-center gap-2">
              <BookOpen className="size-3.5 text-primary" />
              <h4 className="font-display text-[15px] font-medium text-ink">{s.heading}</h4>
            </div>
            <p className="text-[13.5px] leading-relaxed text-foreground whitespace-pre-line">{renderFormattedText(s.body)}</p>
          </div>
        ))}

        {lesson.terms && lesson.terms.length > 0 && (
          <div>
            <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
              Términos clave
            </div>
            <div className="flex flex-wrap gap-2">
              {lesson.terms.map((t) => (
                <div
                  key={t.term}
                  className="rounded-lg border-[1.5px] border-accent bg-accent/40 px-3 py-2"
                >
                  <div className="text-xs font-semibold text-ink">{t.term}</div>
                  <div className="mt-0.5 max-w-56 text-[11px] leading-snug text-muted-foreground">
                    {t.def}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Columna Derecha: Descargas y Acciones */}
      <div className="flex flex-col gap-4">
        <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
          Acciones y Descarga
        </span>

        <div className="rounded-xl border-[1.5px] bg-card p-4.5 flex flex-col gap-4 shadow-(--shadow-soft)">
          <div>
            <h4 className="text-[13px] font-semibold text-ink mb-1">Descargar Fichas</h4>
            <p className="text-[11.5px] text-muted-foreground leading-snug">
              Obtén el contenido de la lección formateado y listo para imprimir o estudiar sin conexión.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            {lesson.pdfUrl ? (
              <button
                type="button"
                onClick={() => triggerDownload(lesson.pdfUrl!, `Leccion_${moduleId}.pdf`, 'pdf')}
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

            {lesson.txtUrl ? (
              <button
                type="button"
                onClick={() => triggerDownload(lesson.txtUrl!, `Leccion_${moduleId}.txt`, 'txt')}
                disabled={downloading !== null}
                className="flex h-9 w-full items-center justify-center gap-1.5 rounded-md bg-primary/10 font-mono text-[11px] font-semibold text-primary transition-colors hover:bg-primary/20 text-center cursor-pointer disabled:opacity-50"
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
      </div>
    </div>
  )
}

function cloneLesson(lesson: LessonContent): LessonContent {
  return {
    ...lesson,
    sections: lesson.sections.map((section) => ({ ...section })),
    terms: lesson.terms.map((term) => ({ ...term })),
  }
}
