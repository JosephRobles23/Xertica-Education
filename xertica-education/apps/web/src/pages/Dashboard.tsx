import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Eyebrow, PageDescription, PageTitle } from '@/components/PageHeader'
import { StatusBadge } from '@/components/content/StatusBadge'
import { ROUTES, routeProgress } from '@/data/routes'
import { cn } from '@/lib/utils'

export default function Dashboard() {
  return (
    <div className="mx-auto max-w-[1080px]">
      <div className="mb-7 flex items-end justify-between gap-5">
        <div>
          <Eyebrow>Estudio de contenido · Impulso 2026</Eyebrow>
          <PageTitle className="text-[32px]">Rutas de aprendizaje</PageTitle>
          <PageDescription>
            Siete rutas en producción. Cada asset pasa por puntos de aprobación humana antes de
            publicarse a Google Classroom.
          </PageDescription>
        </div>
        <Button asChild className="flex-none">
          <Link to="/nueva-ruta">
            <Plus /> Nueva ruta
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-4.5">
        {ROUTES.map((r) => {
          const { done, total, pct } = routeProgress(r)
          const active = r.status === 'en-revision'
          return (
            <Link key={r.id} to={`/ruta/${r.id}`} className="group outline-none">
              <Card
                className={cn(
                  'h-full gap-4 p-5 transition-all group-hover:-translate-y-0.5 group-hover:shadow-(--shadow-soft) group-focus-visible:ring-[3px] group-focus-visible:ring-ring/40',
                  active && 'border-primary',
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[13px] font-semibold text-primary">{r.id}</span>
                  <StatusBadge status={r.status} />
                </div>
                <h3 className="font-display text-lg font-medium leading-snug text-ink">
                  {r.name}
                </h3>
                <div className="mt-auto flex flex-col gap-2">
                  <Progress
                    value={pct}
                    indicatorClassName={r.status === 'aprobado' ? 'bg-success' : 'bg-primary'}
                  />
                  <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                    <span>
                      {done}/{total} módulos
                    </span>
                    <span className="text-foreground">{pct}%</span>
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
