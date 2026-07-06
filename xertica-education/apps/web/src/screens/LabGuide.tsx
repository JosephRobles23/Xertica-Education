'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { ArrowRight, BookOpen, Check, Info, Lightbulb, RefreshCcw, SquarePen, Wrench } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Eyebrow, PageDescription, PageTitle } from '@/components/PageHeader'
import { getRoute } from '@/data/routes'
import { useStore } from '@/store'

export default function LabGuide() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const route = getRoute(id)
  const { approveLabGuide } = useStore()

  if (!route) {
    return (
      <div className="mx-auto max-w-md pt-16 text-center">
        <PageTitle>Ruta no encontrada</PageTitle>
        <Button asChild className="mt-6">
          <Link href="/">Volver a las rutas</Link>
        </Button>
      </div>
    )
  }

  const approve = () => {
    approveLabGuide(route.id)
    toast.success('Guía del laboratorio aprobada', {
      description: 'El laboratorio quedó listo para generarse desde la ruta.',
    })
    router.push(`/ruta/${route.id}`)
  }

  return (
    <div className="mx-auto max-w-[860px]">
      <Eyebrow tone="primary">
        Ruta {route.id} · Laboratorio · Personalización de la guía
      </Eyebrow>
      <PageTitle>Personalizar guía del laboratorio</PageTitle>
      <PageDescription className="mb-6">
        Revisa y personaliza los pasos de la guía práctica antes de generar el material del
        laboratorio.
      </PageDescription>

      <div className="mb-2 flex items-center gap-2">
        <BookOpen className="size-4 text-primary" />
        <h2 className="font-display text-lg font-medium text-ink">Pasos de la guía</h2>
        <span className="ml-auto font-mono text-[11px] text-muted-foreground">
          {route.pack.lab.steps.length} pasos definidos
        </span>
      </div>
      <p className="mb-4 text-[13px] text-muted-foreground">
        Cada paso guía al participante a través de la herramienta, con instrucciones claras y tips
        prácticos.
      </p>

      <div className="mb-8 flex flex-col gap-3.5">
        {route.pack.lab.steps.map((step, i) => (
          <Card key={step.title} className="gap-3 p-4.5">
            <div className="flex items-center gap-3">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary font-mono text-[11px] font-bold text-white">
                {i + 1}
              </span>
              <div className="flex-1">
                <h3 className="text-[14.5px] font-semibold text-ink">{step.title}</h3>
              </div>
              {step.tool && (
                <Badge>
                  <Wrench className="size-3" /> {step.tool}
                </Badge>
              )}
            </div>
            <p className="pl-10 text-[13.5px] leading-relaxed">{step.desc}</p>
            {step.tip && (
              <div className="ml-10 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-950/20">
                <Lightbulb className="mt-0.5 size-3.5 text-amber-500" />
                <span className="text-[12px] leading-snug text-amber-800 dark:text-amber-200">
                  {step.tip}
                </span>
              </div>
            )}
          </Card>
        ))}
      </div>

      <Card className="mb-6 flex-row items-start gap-3.5 border-accent bg-primary/8 p-4.5">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        <div>
          <div className="mb-1 text-[13.5px] font-semibold text-ink">
            Al aprobar se habilita la generación del laboratorio
          </div>
          <p className="text-[13px] leading-relaxed">
            Revisa los pasos, herramientas y tips. Al aprobar, volverás a la ruta con el laboratorio
            listo para generar.
          </p>
        </div>
      </Card>

      <div className="flex items-center justify-end gap-3">
        <Button
          variant="outline"
          onClick={() =>
            toast.info('Editor de pasos', {
              description: 'Disponible en la siguiente iteración del estudio.',
            })
          }
        >
          <SquarePen /> Editar pasos
        </Button>
        <Button
          variant="outline"
          onClick={() =>
            toast.info('Regenerando guía…', {
              description: 'La IA propondrá pasos alternativos basados en el corpus.',
            })
          }
        >
          <RefreshCcw /> Regenerar
        </Button>
        <Button onClick={approve}>
          <Check /> Aprobar <ArrowRight />
        </Button>
      </div>
    </div>
  )
}
