import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, Check, Info, RefreshCcw, SquarePen } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Eyebrow, PageDescription, PageTitle } from '@/components/PageHeader'
import { getRoute } from '@/data/routes'
import { useStore } from '@/store'

const SCRIPT_BLOCKS = [
  { tag: 'Conceptual', used: 210, budget: 260, text: 'Abrimos definiendo la idea núcleo del módulo: qué cambia, por qué importa y contra qué fuentes se verifica cada afirmación.' },
  { tag: 'Walkthrough', used: 240, budget: 300, text: 'Recorremos un ejemplo real paso a paso, mostrando cómo cada supuesto se contrasta con las fuentes aprobadas del corpus.' },
  { tag: 'Onboarding', used: 150, budget: 200, text: 'Cerramos con una acción concreta para el equipo: cómo aplicar lo aprendido en su propio flujo de trabajo esta semana.' },
] as const

export default function Storyboard() {
  const { id } = useParams()
  const nav = useNavigate()
  const route = getRoute(id)
  const { approveStoryboard } = useStore()

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

  const approve = () => {
    approveStoryboard(route.id)
    toast.success('Guion y storyboard aprobados', {
      description: 'El video quedó listo para generarse desde la ruta.',
    })
    nav(`/ruta/${route.id}`)
  }

  return (
    <div className="mx-auto max-w-[860px]">
      <Eyebrow tone="primary">
        Ruta {route.id} · Video · Aprobación previa al render
      </Eyebrow>
      <PageTitle>Revisar guion y storyboard</PageTitle>
      <PageDescription className="mb-6">
        Aprueba el guion y el storyboard de «{route.pack.video.caption}» antes de generar el
        contenido del video.
      </PageDescription>

      <h2 className="mb-1 font-display text-lg font-medium text-ink">Guion segmentado</h2>
      <p className="mb-4 text-[13px] text-muted-foreground">
        Tres bloques narrativos ajustados a la duración objetivo ({route.pack.video.duration}).
      </p>

      <div className="mb-8 flex flex-col gap-3.5">
        {SCRIPT_BLOCKS.map((b) => {
          const pct = Math.round((b.used / b.budget) * 100)
          return (
            <Card key={b.tag} className="gap-3 p-4.5">
              <div className="flex items-center justify-between">
                <Badge>{b.tag}</Badge>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {b.used} / {b.budget} palabras
                </span>
              </div>
              <p className="text-sm leading-relaxed">{b.text}</p>
              <Progress value={pct} indicatorClassName="bg-success" className="h-1.25" />
            </Card>
          )
        })}
      </div>

      <h2 className="mb-1 font-display text-lg font-medium text-ink">Storyboard</h2>
      <p className="mb-4 text-[13px] text-muted-foreground">
        {route.pack.video.segments.length + 2} escenas · previsualización antes del render.
      </p>
      <div className="mb-8 grid grid-cols-5 gap-3">
        {['Título · concepto', 'Diagrama de pasos', 'Ejemplo en vivo', 'Verificación de fuente', 'Cierre · acción'].map(
          (label, i) => (
            <div key={label} className="flex flex-col gap-1.5">
              <div
                className={`flex aspect-[16/10] items-center justify-center rounded-lg border-[1.5px] bg-gradient-to-br ${
                  i === 0 ? route.pack.video.gradient : ''
                } ${i === 0 ? '' : 'bg-[repeating-linear-gradient(135deg,#F5F3FB,#F5F3FB_7px,#EEEAF9_7px,#EEEAF9_14px)]'}`}
              >
                {i === 0 ? (
                  <span className="text-xl drop-shadow">{route.pack.video.emoji}</span>
                ) : (
                  <span className="font-mono text-[13px] font-semibold text-input">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                )}
              </div>
              <span className="text-center font-mono text-[9.5px] leading-snug text-muted-foreground">
                {label}
              </span>
            </div>
          ),
        )}
      </div>

      <Card className="mb-6 flex-row items-start gap-3.5 border-accent bg-primary/8 p-4.5">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <div className="mb-1 text-[13.5px] font-semibold text-ink">
            Al aprobar se habilita el render con Veo
          </div>
          <p className="text-[13px] leading-relaxed">
            Revisa el guion y el storyboard con cuidado. Al aprobar, volverás a la ruta con el
            video listo para generar su material.
          </p>
        </div>
      </Card>

      <div className="flex items-center justify-end gap-3">
        <Button variant="outline" onClick={() => toast.info('Editor de guion', { description: 'Disponible en la siguiente iteración del estudio.' })}>
          <SquarePen /> Editar guion
        </Button>
        <Button variant="outline" onClick={() => toast.info('Regenerando propuesta…', { description: 'La IA propondrá un guion alternativo.' })}>
          <RefreshCcw /> Regenerar
        </Button>
        <Button onClick={approve}>
          <Check /> Aprobar <ArrowRight />
        </Button>
      </div>
    </div>
  )
}
