import { Badge } from '@/shared/ui/badge'
import { cn } from '@/shared/lib/utils'
import { STATUS_LABEL, type ContentStatus } from '@/shared/lib/types'

const VARIANT: Record<ContentStatus, 'muted' | 'default' | 'success'> = {
  borrador: 'muted',
  generado: 'default',
  'en-revision': 'default',
  aprobado: 'success',
}

const DOT: Record<ContentStatus, string> = {
  borrador: 'bg-muted-foreground',
  generado: 'bg-primary',
  'en-revision': 'bg-primary',
  aprobado: 'bg-success',
}

export function StatusBadge({ status, className }: { status: ContentStatus; className?: string }) {
  return (
    <Badge variant={VARIANT[status]} className={className}>
      <span
        className={cn(
          'size-[5px] rounded-full',
          DOT[status],
          status === 'en-revision' && 'animate-pulse-dot',
        )}
      />
      {STATUS_LABEL[status]}
    </Badge>
  )
}
