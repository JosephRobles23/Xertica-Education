import { useState } from 'react'
import { ChevronDown, ChevronRight, ExternalLink, Play } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { SourceVideoPreview as SourceVideoPreviewData } from '@/shared/lib/types'

/**
 * Preview colapsable del video de YouTube encontrado por el agente de
 * deep research para una fuente del corpus. Cuando la fuente trae un
 * `youtubeId` real, se embebe el reproductor oficial tras el primer clic;
 * si no, se muestra el placeholder ilustrativo de la cápsula.
 */
export function SourceVideoPreview({
  preview,
  open,
  onOpenChange,
}: {
  preview: SourceVideoPreviewData
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [playing, setPlaying] = useState(false)
  const hasRealVideo = Boolean(preview.youtubeId)

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => {
          if (open) setPlaying(false)
          onOpenChange(!open)
        }}
        className="flex cursor-pointer items-center gap-1.5 text-[12.5px] font-medium text-primary outline-none hover:text-primary/80 focus-visible:ring-[3px] focus-visible:ring-ring/30 rounded-md"
      >
        {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
        {open ? 'Ocultar preview del video' : 'Ver preview del video'}
      </button>

      {open && (
        <div className={cn('mt-2.5', hasRealVideo ? 'max-w-md' : 'max-w-xs')}>
          {playing && preview.youtubeId ? (
            <div className="overflow-hidden rounded-lg shadow-(--shadow-soft)">
              <iframe
                className="aspect-video w-full"
                src={`https://www.youtube-nocookie.com/embed/${preview.youtubeId}?autoplay=1`}
                title={preview.videoTitle ?? preview.channel}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => hasRealVideo && setPlaying(true)}
              className={cn(
                'group relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg shadow-(--shadow-soft)',
                hasRealVideo ? 'cursor-pointer bg-ink' : cn('cursor-default bg-gradient-to-br', preview.gradient),
              )}
            >
              {hasRealVideo ? (
                <img
                  src={`https://i.ytimg.com/vi/${preview.youtubeId}/hqdefault.jpg`}
                  alt={preview.videoTitle ?? preview.channel}
                  className="absolute inset-0 size-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
                />
              ) : (
                <span
                  aria-hidden
                  className="absolute top-1/2 right-[14%] -translate-y-1/2 select-none text-4xl opacity-90 drop-shadow-lg transition-transform duration-300 group-hover:scale-110"
                >
                  {preview.emoji}
                </span>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-ink/60 via-transparent to-ink/10" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex size-11 items-center justify-center rounded-full border-[1.5px] border-white/40 bg-white/15 backdrop-blur-sm transition-all group-hover:scale-105 group-hover:bg-white/25">
                  <Play className="ml-0.5 size-4 fill-white text-white" />
                </div>
              </div>
              <span className="absolute right-3 bottom-2.5 rounded-md bg-ink/50 px-1.5 py-0.5 font-mono text-[10px] text-white/90 backdrop-blur-sm">
                {preview.duration}
              </span>
            </button>
          )}

          <div className="mt-1.5 flex items-center justify-between gap-2">
            <span className="min-w-0 truncate font-mono text-[10.5px] text-muted-foreground">
              {preview.channel}
              {preview.videoTitle ? ` · ${preview.videoTitle}` : ''}
            </span>
            {hasRealVideo && (
              <a
                href={`https://www.youtube.com/watch?v=${preview.youtubeId}`}
                target="_blank"
                rel="noreferrer"
                className="flex shrink-0 items-center gap-1 text-[11px] font-medium text-primary hover:underline"
              >
                YouTube <ExternalLink className="size-3" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
