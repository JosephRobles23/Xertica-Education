import { BookOpen } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { LessonContent } from '@/shared/lib/types'

/** Lesson: secciones de texto + glosario de términos clave. */
export function LessonView({ lesson, className }: { lesson: LessonContent; className?: string }) {
  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {lesson.sections.map((s) => (
        <div key={s.heading} className="rounded-xl border-[1.5px] bg-card p-4.5">
          <div className="mb-1.5 flex items-center gap-2">
            <BookOpen className="size-3.5 text-primary" />
            <h4 className="font-display text-[15px] font-medium text-ink">{s.heading}</h4>
          </div>
          <p className="text-[13.5px] leading-relaxed text-foreground">{s.body}</p>
        </div>
      ))}

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
    </div>
  )
}
