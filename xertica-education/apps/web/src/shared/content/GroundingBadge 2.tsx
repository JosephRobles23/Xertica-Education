import { BookMarked, BookDashed } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { GroundingStatus } from '@/shared/lib/types'

/** Badge honesto del origen del contenido (ADR-0023): anclado a documentos del
 * cliente (KB) o generado solo desde el objetivo del módulo. */
export function GroundingBadge({ status, className }: { status?: GroundingStatus; className?: string }) {
  if (!status) return null
  const kbGrounded = status === 'kb-grounded'
  return (
    <span
      title={
        kbGrounded
          ? 'Contenido anclado a los documentos del cliente indexados en la Knowledge Base.'
          : 'Sin documentos del cliente en la Knowledge Base: contenido generado desde el objetivo del módulo.'
      }
      className={cn(
        'inline-flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.06em]',
        kbGrounded
          ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
          : 'border-amber-300 bg-amber-50 text-amber-700',
        className,
      )}
    >
      {kbGrounded ? <BookMarked className="size-3" /> : <BookDashed className="size-3" />}
      {kbGrounded ? 'Anclado a KB' : 'Sin grounding KB'}
    </span>
  )
}
