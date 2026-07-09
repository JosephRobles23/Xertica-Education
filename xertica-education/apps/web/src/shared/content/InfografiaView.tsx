import { CheckCircle2 } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { InfografiaContent } from '@/shared/lib/types'

/** Infografía de una página (proporción A4) con bullets y footer. */
export function InfografiaView({
  info,
  compact = false,
  className,
}: {
  info: InfografiaContent
  compact?: boolean
  className?: string
}) {
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
