import { Link, useParams } from 'react-router-dom'
import { Check, CircleCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageTitle } from '@/components/PageHeader'
import { getRoute } from '@/data/routes'

export default function Publicado() {
  const { id } = useParams()
  const route = getRoute(id)

  if (!route) {
    return (
      <div className="mx-auto max-w-md pt-16 text-center">
        <PageTitle>Ruta no encontrada</PageTitle>
        <Button asChild className="mt-6">
          <Link to="/">Volver a las rutas</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[680px] pt-5 text-center">
      <div className="mx-auto mb-5 flex size-16 items-center justify-center rounded-full border-[1.5px] border-success bg-success/12">
        <Check className="size-7 text-success" strokeWidth={2.5} />
      </div>
      <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-success">
        Publicado
      </div>
      <PageTitle className="mb-3">Asset aprobado y listo</PageTitle>
      <p className="mx-auto mb-8 max-w-md text-[14.5px] leading-relaxed text-muted-foreground">
        El contenido de «{route.name}» se publicó. 
      </p>

      <Card className="mb-6 flex-row items-center gap-3 border-success bg-success/10 p-4.5 text-left">
        <CircleCheck className="size-4 shrink-0 text-success" />
        <span className="text-[13.5px] leading-relaxed">
          Publicado a <b className="text-ink">Classroom · {route.name}</b> — visible para 34
          estudiantes inscritos.
        </span>
      </Card>

      <Card className="mb-7 gap-4 p-6 text-left">
        <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          Resumen de la ruta
        </div>
        <div className="grid grid-cols-2 gap-5">
          <div>
            <div className="mb-1 text-[11px] text-muted-foreground">Componentes publicados</div>
            <div className="text-[15px] text-ink">Video · Infografía · Quiz · Laboratorio</div>
          </div>
          <div>
            <div className="mb-1 text-[11px] text-muted-foreground">Fuentes verificadas</div>
            <div className="text-[15px] text-ink">
              {route.sources.filter((s) => s.verified).length} de {route.sources.length} citadas
            </div>
          </div>
          <div>
            <div className="mb-1 text-[11px] text-muted-foreground">Aprobaciones humanas</div>
            <div className="text-[15px] text-success">3 de 3 · completas</div>
          </div>
          <div>
            <div className="mb-1 text-[11px] text-muted-foreground">Estado</div>
            <div className="text-[15px] text-ink">Publicado</div>
          </div>
        </div>
      </Card>

      <div className="flex justify-center gap-3">
        <Button asChild>
          <Link to={`/ruta/${route.id}`}>Volver a la ruta</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/">Ver todas las rutas</Link>
        </Button>
      </div>
    </div>
  )
}
