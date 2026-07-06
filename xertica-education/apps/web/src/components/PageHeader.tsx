import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function Eyebrow({
  children,
  tone = 'muted',
  className,
}: {
  children: ReactNode
  tone?: 'muted' | 'primary' | 'success'
  className?: string
}) {
  return (
    <div
      className={cn(
        'eyebrow mb-3',
        tone === 'primary' && 'text-primary',
        tone === 'success' && 'text-success',
        tone === 'muted' && 'text-muted-foreground',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function PageTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h1
      className={cn(
        'font-display text-3xl font-medium tracking-tight text-ink',
        className,
      )}
    >
      {children}
    </h1>
  )
}

export function PageDescription({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn('mt-1.5 max-w-xl text-[14.5px] leading-relaxed text-muted-foreground', className)}>
      {children}
    </p>
  )
}
