'use client'

import { Fragment, type ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { getRoute } from '@/shared/data/routes'

interface Crumb {
  label: string
  to?: string
  accent?: 'ink' | 'success'
}

function crumbsFor(pathname: string): Crumb[] {
  const rutas: Crumb = { label: 'Rutas', to: '/' }
  const seg = pathname.split('/').filter(Boolean)

  if (pathname === '/') return [{ label: 'Rutas', accent: 'ink' }]
  if (pathname === '/nueva-ruta') return [rutas, { label: 'Nueva ruta', accent: 'ink' }]
  if (pathname === '/estructura-propuesta')
    return [rutas, { label: 'Nueva ruta', to: '/nueva-ruta' }, { label: 'Estructura propuesta', accent: 'ink' }]
  if (pathname === '/biblioteca') return [{ label: 'Biblioteca', accent: 'ink' }]

  if (seg[0] === 'ruta' && seg[1]) {
    const id = seg[1]
    const sub = seg[2]
    const route = getRoute(id)
    const base: Crumb = { label: `Ruta ${id}`, to: `/ruta/${id}` }
    if (sub === 'video-storyboard') return [rutas, base, { label: 'Guion y storyboard', accent: 'ink' }]
    if (sub === 'lab-guia') return [rutas, base, { label: 'Guía del laboratorio', accent: 'ink' }]
    if (sub === 'asset-final') return [rutas, base, { label: 'Asset final', accent: 'ink' }]
    if (sub === 'publicado') return [rutas, base, { label: 'Publicado', accent: 'success' }]
    return [rutas, { label: route ? `Ruta ${route.id}` : 'Ruta', accent: 'ink' }]
  }
  return [{ label: 'Rutas', accent: 'ink' }]
}

const NAV = [
  { label: 'Rutas', to: '/', enabled: true },
  { label: 'Biblioteca', to: '/biblioteca', enabled: true },
] as const

export default function Layout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const crumbs = crumbsFor(pathname)

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* TOPBAR */}
      <header className="sticky top-0 z-20 flex h-[62px] flex-none items-center gap-5 border-b-[1.5px] bg-card px-6">
        <Link href="/" className="flex items-center gap-2.5 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/40 rounded-lg">
          <span className="flex size-[30px] items-center justify-center rounded-lg bg-gradient-to-br from-primary to-fuchsia-500 font-display text-[17px] font-bold text-white shadow-[0_3px_10px_rgba(124,58,237,.35)]">
            X
          </span>
          <span className="font-display text-lg font-semibold tracking-tight text-ink">
            xertica<span className="text-primary">.education</span>
          </span>
        </Link>

        <nav aria-label="breadcrumb" className="ml-2 flex items-center gap-2 font-mono text-[11.5px]">
          {crumbs.map((c, i) => (
            <Fragment key={`${c.label}-${i}`}>
              {i > 0 && <ChevronRight className="size-3 text-input" />}
              {c.to ? (
                <Link href={c.to} className="text-muted-foreground transition-colors hover:text-ink">
                  {c.label}
                </Link>
              ) : (
                <span className={cn(c.accent === 'success' ? 'text-success' : 'text-ink')}>
                  {c.label}
                </span>
              )}
            </Fragment>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-4">
          <span className="font-mono text-[11px] text-muted-foreground">Impulso 2026</span>
          <div className="flex size-8 items-center justify-center rounded-full bg-accent font-mono text-xs font-semibold text-ink">
            MR
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* SIDEBAR */}
        <nav className="flex w-[214px] flex-none flex-col gap-1 bg-sidebar px-3.5 py-5.5">
          <div className="px-2.5 pt-1.5 pb-3 font-mono text-[10px] uppercase tracking-[0.12em] text-sidebar-muted">
            Estudio
          </div>
          {NAV.map((n) => {
            const isRutas = n.label === 'Rutas'
            const isBiblioteca = n.label === 'Biblioteca'
            const active =
              (isRutas && (pathname === '/' || pathname.startsWith('/nueva') || pathname.startsWith('/estructura') || pathname.startsWith('/ruta'))) ||
              (isBiblioteca && pathname === '/biblioteca')
            return (
              <Link
                key={n.label}
                href={n.to}
                className={cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-[13.5px] outline-none transition-colors focus-visible:ring-[3px] focus-visible:ring-ring/40',
                  active
                    ? 'bg-primary/28 font-semibold text-white'
                    : 'font-medium text-sidebar-foreground hover:bg-white/5 hover:text-white',
                )}
              >
                <span
                  className={cn(
                    'size-1.5 rounded-[2px]',
                    active ? 'bg-lime' : 'bg-white/20',
                  )}
                />
                {n.label}
              </Link>
            )
          })}
        </nav>

        {/* CONTENT */}
        <main className="min-w-0 flex-1 overflow-x-hidden px-11 pt-8 pb-20">
          <div key={pathname} className="animate-in fade-in slide-in-from-bottom-1 duration-300">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
