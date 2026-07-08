'use client'

import { useState } from 'react'
import { CheckCircle2, Download, Loader2, Sparkles } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { InfografiaContent, AspectRatio } from '@/shared/lib/types'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Textarea } from '@/shared/ui/textarea'

/** Infografía de una página con bullets y footer. */
export function InfografiaView({
  info,
  compact = false,
  className,
  routeId,
}: {
  info: InfografiaContent
  compact?: boolean
  className?: string
  routeId?: string
}) {
  const [feedback, setFeedback] = useState('')
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>(info?.aspectRatio || 'vertical')
  const [regenerating, setRegenerating] = useState(false)
  const [downloading, setDownloading] = useState<string | null>(null)
  const { fetchRoutes } = useStore()

  const handleRegenerate = async (targetRatio?: AspectRatio) => {
    if (!routeId) return
    const ratioToUse = targetRatio || aspectRatio
    setRegenerating(true)
    const toastId = toast.loading('Regenerando infografía con tu feedback...', {
      description: `Llamando a OpenAI (gpt-image-2) con formato ${ratioToUse}...`,
    })
    try {
      await api.request(`/learning-paths/${routeId}/infographic/regenerate`, {
        method: 'POST',
        body: JSON.stringify({ 
          user_prompt: feedback,
          aspect_ratio: ratioToUse
        }),
      })
      await fetchRoutes()
      toast.success('Infografía regenerada con éxito', { id: toastId })
      setFeedback('')
    } catch (e) {
      console.error(e)
      toast.error('Error al regenerar la infografía', {
        id: toastId,
        description: e instanceof Error ? e.message : 'Error desconocido',
      })
    } finally {
      setRegenerating(false)
    }
  }

  // Programmatically fetches and triggers a direct browser download
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

  if (info?.imageUrl) {
    const isHorizontal = info.aspectRatio === 'horizontal'
    const isSquare = info.aspectRatio === 'square'

    const containerWidth = compact 
      ? 'w-72' 
      : isHorizontal 
        ? 'w-160' 
        : isSquare 
          ? 'w-120' 
          : 'w-120'

    const imageAspect = isHorizontal 
      ? 'aspect-[1.77/1]' 
      : isSquare 
        ? 'aspect-square' 
        : 'aspect-[1/1.5]'

    return (
      <div className={cn('flex flex-col items-center gap-4', className)}>
        <div
          className={cn(
            'flex flex-col gap-3 rounded-lg border-[1.5px] bg-card p-5 shadow-(--shadow-soft) items-center',
            containerWidth,
          )}
        >
          <div className="font-mono text-[9px] uppercase tracking-[0.1em] text-primary w-full flex justify-between items-center">
            <span>Infografía · Imagen Generada por IA</span>
            {info.aspectRatio && (
              <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[8px] font-semibold capitalize">
                Formato: {info.aspectRatio}
              </span>
            )}
          </div>
          <div className={cn('relative overflow-hidden rounded-md border border-secondary w-full bg-muted flex items-center justify-center', imageAspect)}>
            {regenerating ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="size-8 animate-spin text-primary" />
                <span className="text-xs text-muted-foreground font-medium">Generando con IA...</span>
              </div>
            ) : (
              <img src={info.imageUrl} alt={info.title} className="w-full h-full object-contain" />
            )}
          </div>
          {info.title && <div className="text-xs font-semibold text-center mt-1 text-ink">{info.title}</div>}

          {/* Download footer */}
          <div className="flex gap-2 w-full mt-2">
            <button
              onClick={() => triggerDownload(info.imageUrl!, `${info.title || 'infografia'}.png`, 'png')}
              disabled={downloading !== null}
              className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-md bg-primary/10 font-mono text-[10px] font-semibold text-primary transition-colors hover:bg-primary/20 text-center cursor-pointer disabled:opacity-50"
            >
              <Download className="size-3" /> Descargar PNG
            </button>
            
            {info.pdfUrl ? (
              <button
                onClick={() => triggerDownload(info.pdfUrl!, `${info.title || 'infografia'}.pdf`, 'pdf')}
                disabled={downloading !== null}
                className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-md bg-success/12 font-mono text-[10px] font-semibold text-success transition-colors hover:bg-success/20 text-center cursor-pointer disabled:opacity-50"
              >
                <Download className="size-3" /> Descargar PDF
              </button>
            ) : (
              <div className="flex h-8 flex-1 items-center justify-center rounded-md bg-success/12 font-mono text-[10px] font-semibold text-success opacity-50">
                PDF no disponible
              </div>
            )}
          </div>
        </div>

        {/* Feedback Section (only visible if routeId is provided and we're not compact) */}
        {routeId && !compact && (
          <div className={cn('flex flex-col gap-3.5 rounded-lg border-[1.5px] border-input bg-card p-4 shadow-sm', containerWidth)}>
            <div className="text-[13px] font-semibold text-ink flex items-center gap-1.5">
              <Sparkles className="size-4 text-primary" />
              ¿Quieres ajustar el diseño o cambiar formato?
            </div>
            
            {/* Format selector */}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Cambiar Relación de Aspecto:</span>
              <div className="flex gap-1.5 flex-wrap">
                {(['vertical', 'horizontal', 'square', 'auto'] as const).map((ratio) => (
                  <Button
                    key={ratio}
                    size="sm"
                    variant={aspectRatio === ratio ? 'primary' : 'outline'}
                    className="capitalize text-[10.5px] h-7 px-2.5"
                    onClick={() => {
                      setAspectRatio(ratio)
                      // Proactively regenerate with the new ratio if they clicked it directly
                      handleRegenerate(ratio)
                    }}
                    disabled={regenerating}
                  >
                    {ratio === 'auto' ? 'Automático' : ratio}
                  </Button>
                ))}
              </div>
            </div>

            <div className="h-px bg-secondary" />

            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Ajuste de contenido / prompt adicional:</span>
              <p className="text-[11px] text-muted-foreground leading-snug">
                Describe los cambios que te gustaría ver (colores, distribución, detalles) y la IA generará una nueva versión.
              </p>
              <Textarea
                rows={2}
                placeholder="Ej: Utiliza colores neón más llamativos y coloca el logotipo centrado..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                disabled={regenerating}
                className="text-[12px] min-h-[50px] resize-none"
              />
              <div className="flex justify-end mt-1">
                <Button
                  size="sm"
                  onClick={() => handleRegenerate()}
                  disabled={regenerating || !feedback.trim()}
                  className="text-xs"
                >
                  {regenerating ? (
                    <>
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                      Regenerando...
                    </>
                  ) : (
                    'Aplicar y Regenerar'
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={cn('flex justify-center', className)}>
      <div
        className={cn(
          'flex aspect-[1/1.35] flex-col gap-3.5 rounded-lg border-[1.5px] bg-card p-6 shadow-(--shadow-soft)',
          compact ? 'w-72' : 'w-85',
        )}
      >
        <div className="font-mono text-[9px] uppercase tracking-[0.1em] text-primary">
          Infografía · 1 página
        </div>
        <div className="font-display text-lg leading-tight text-ink">{info.title}</div>
        <div className="h-px bg-secondary" />

        <div className="flex flex-col gap-2.5">
          {info.bullets.map((b) => (
            <div key={b} className="flex items-start gap-2.5">
              <CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-primary" />
              <span className="text-xs leading-snug">{b}</span>
            </div>
          ))}
        </div>

        {/* Diagrama de pasos */}
        <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-lg bg-[repeating-linear-gradient(135deg,#F5F3FB,#F5F3FB_7px,#EEEAF9_7px,#EEEAF9_14px)] p-3">
          <div className="flex items-center gap-1.5">
            {[1, 2, 3].map((n) => (
              <div key={n} className="flex items-center gap-1.5">
                <span className="flex size-6 items-center justify-center rounded-full bg-primary/15 font-mono text-[10px] font-bold text-primary">
                  {n}
                </span>
                {n < 3 && <span className="h-px w-4 bg-input" />}
              </div>
            ))}
          </div>
          <span className="font-mono text-[9px] text-input">diagrama de pasos</span>
        </div>

        <div className="flex gap-2">
          <div className="flex h-8 flex-1 items-center justify-center rounded-md bg-primary/10 font-mono text-[10px] font-semibold text-primary">
            {info.footer[0]}
          </div>
          <div className="flex h-8 flex-1 items-center justify-center rounded-md bg-success/12 font-mono text-[10px] font-semibold text-success">
            {info.footer[1]}
          </div>
        </div>
      </div>
    </div>
  )
}
