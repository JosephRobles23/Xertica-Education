import { useState } from 'react'
import { BookOpen, ChevronDown, ChevronRight, CircleCheck, Lightbulb, Wrench } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { LabContent } from '@/shared/lib/types'

export function LabView({ lab, className }: { lab: LabContent; className?: string }) {
  const [openStep, setOpenStep] = useState(0)
  const [completed, setCompleted] = useState<Set<number>>(new Set())

  const toggle = (i: number) => setOpenStep(openStep === i ? -1 : i)

  const markComplete = (i: number) => {
    setCompleted((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="mb-1 flex items-center gap-2">
        <BookOpen className="size-4 text-primary" />
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          Guia paso a paso
        </span>
        <span className="ml-auto font-mono text-[11px] text-muted-foreground">
          {completed.size}/{lab.steps.length} completados
        </span>
      </div>

      {lab.steps.map((step, i) => {
        const isOpen = openStep === i
        const isDone = completed.has(i)

        return (
          <div
            key={step.title}
            className={cn(
              'rounded-xl border-[1.5px] transition-colors',
              isDone
                ? 'border-success/40 bg-success/5'
                : isOpen
                  ? 'border-primary bg-primary/5'
                  : 'border-border bg-card',
            )}
          >
            <button
              type="button"
              onClick={() => toggle(i)}
              className="flex w-full cursor-pointer items-center gap-3 px-4 py-3.5 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30 rounded-xl"
            >
              <span
                className={cn(
                  'flex size-7 shrink-0 items-center justify-center rounded-full font-mono text-[11px] font-bold',
                  isDone
                    ? 'bg-success/15 text-success'
                    : isOpen
                      ? 'bg-primary text-white'
                      : 'bg-secondary text-muted-foreground',
                )}
              >
                {isDone ? <CircleCheck className="size-4" /> : i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <span className="block text-[14px] font-semibold text-ink">{step.title}</span>
                {!isOpen && (
                  <span className="mt-0.5 block text-[12.5px] leading-snug text-muted-foreground line-clamp-1">
                    {step.desc}
                  </span>
                )}
              </div>
              {isOpen ? (
                <ChevronDown className="size-4 text-input" />
              ) : (
                <ChevronRight className="size-4 text-input" />
              )}
            </button>

            {isOpen && (
              <div className="border-t border-secondary px-4 pt-3 pb-4 pl-14">
                <p className="mb-3 text-[13.5px] leading-relaxed">{step.desc}</p>

                {step.tool && (
                  <div className="mb-2 flex items-center gap-2 rounded-lg bg-secondary px-3 py-2">
                    <Wrench className="size-3.5 text-primary" />
                    <span className="text-[12px] font-medium text-ink">Herramienta:</span>
                    <span className="text-[12px] text-muted-foreground">{step.tool}</span>
                  </div>
                )}

                {step.tip && (
                  <div className="mb-3 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-950/20">
                    <Lightbulb className="mt-0.5 size-3.5 text-amber-500" />
                    <span className="text-[12px] leading-snug text-amber-800 dark:text-amber-200">
                      {step.tip}
                    </span>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => markComplete(i)}
                  className={cn(
                    'mt-1 flex cursor-pointer items-center gap-2 rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30',
                    isDone
                      ? 'bg-success/10 text-success hover:bg-success/15'
                      : 'bg-secondary text-muted-foreground hover:bg-accent hover:text-ink',
                  )}
                >
                  <CircleCheck className="size-3.5" />
                  {isDone ? 'Completado' : 'Marcar como completado'}
                </button>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
