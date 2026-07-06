import { Play } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { VideoContent } from '@/shared/lib/types'

/**
 * Fotograma del video: portada 16:9 con la escena de la cápsula,
 * botón de reproducción y tira de segmentos.
 */
export function VideoFrame({
  video,
  compact = false,
  className,
}: {
  video: VideoContent
  compact?: boolean
  className?: string
}) {
  return (
    <div className={className}>
      <div
        className={cn(
          'group relative flex cursor-pointer items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br shadow-(--shadow-soft)',
          video.gradient,
          compact ? 'aspect-video max-w-md' : 'aspect-video',
        )}
      >
        {/* Escena del fotograma */}
        <span
          aria-hidden
          className={cn(
            'absolute top-1/2 right-[14%] -translate-y-1/2 select-none opacity-90 drop-shadow-lg transition-transform duration-300 group-hover:scale-110',
            compact ? 'text-5xl' : 'text-7xl',
          )}
        >
          {video.emoji}
        </span>
        <div className="absolute inset-0 bg-gradient-to-t from-ink/60 via-transparent to-ink/20" />

        {/* Play */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex size-14 items-center justify-center rounded-full border-[1.5px] border-white/40 bg-white/15 backdrop-blur-sm transition-all group-hover:scale-105 group-hover:bg-white/25">
            <Play className="ml-0.5 size-5 fill-white text-white" />
          </div>
        </div>

        {/* Overlays */}
        <span className="absolute top-3 left-4 font-mono text-[10px] uppercase tracking-[0.06em] text-white/70">
          Cápsula · Veo 3
        </span>
        <span className="absolute right-4 bottom-3 rounded-md bg-ink/50 px-2 py-0.5 font-mono text-[11px] text-white/90 backdrop-blur-sm">
          {video.duration}
        </span>
        <span className="absolute bottom-3 left-4 max-w-[70%] font-display text-sm font-medium text-white drop-shadow">
          {video.caption}
        </span>
      </div>

      {/* Segmentos */}
      {!compact && (
        <div className="mt-4">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
            Segmentos
          </div>
          <div className="divide-y divide-secondary">
            {video.segments.map((s) => (
              <div key={s.at} className="flex items-center gap-4 py-2.5">
                <span className="w-11 font-mono text-xs text-primary">{s.at}</span>
                <span className="flex-1 text-[13.5px]">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
