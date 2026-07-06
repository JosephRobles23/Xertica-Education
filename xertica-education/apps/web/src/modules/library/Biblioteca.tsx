'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Check, ClipboardCopy, Download, Eye } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Separator } from '@/shared/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { ROUTES } from '@/shared/data/routes'
import { KIND_LABEL, STATUS_LABEL } from '@/shared/lib/types'
import type { LearningRoute, RouteModule } from '@/shared/lib/types'
import { useStore } from '@/shared/store'

function getAssetCount(route: LearningRoute) {
  return route.modules.reduce((total, module) => total + module.contents.length, 0)
}

function copyToClipboard(route: LearningRoute) {
  const text = [
    `[Xertica Education] Curso publicado: ${route.name}`,
    route.objective,
    `Ruta ${route.id} · ${route.modules.length} módulos · ${getAssetCount(route)} assets aprobados`,
    'Módulos:',
    ...route.modules.map((module) => `${module.num}. ${module.name} (${module.type})`),
  ].join('\n')

  navigator.clipboard.writeText(text).then(
    () => toast.success('Curso copiado al portapapeles', { description: `«${route.name}» listo para Classroom.` }),
    () => toast.error('No se pudo copiar'),
  )
}

function downloadMock(route: LearningRoute) {
  toast.info('Descarga simulada', {
    description: `Paquete completo de «${route.name}» (${route.id}_curso_publicado.zip)`,
  })
}

function ModuleRow({ route, module }: { route: LearningRoute; module: RouteModule }) {
  const { moduleStatusOf } = useStore()
  const preview = module.contents.slice(0, 4)
  const status = moduleStatusOf(route.id, module)

  return (
    <div className="rounded-lg border-[1.5px] border-border px-3.5 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] font-semibold text-primary">{module.num}</span>
        <span className="min-w-0 flex-1 text-[13px] font-semibold text-ink">{module.name}</span>
        <Badge variant={status === 'aprobado' ? 'success' : 'muted'}>
          {STATUS_LABEL[status]}
        </Badge>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {preview.map((content) => (
          <span
            key={content.kind}
            className="rounded-full bg-secondary px-2 py-1 font-mono text-[10px] text-muted-foreground"
          >
            {KIND_LABEL[content.kind]}
          </span>
        ))}
        {module.contents.length > preview.length ? (
          <span className="rounded-full bg-secondary px-2 py-1 font-mono text-[10px] text-muted-foreground">
            +{module.contents.length - preview.length}
          </span>
        ) : null}
      </div>
    </div>
  )
}

function CourseLibraryCard({ route }: { route: LearningRoute }) {
  const { routeStatusOf, routeProgressOf } = useStore()
  const status = routeStatusOf(route)
  const progress = routeProgressOf(route)
  const isPublished = status === 'aprobado'
  const assetCount = getAssetCount(route)

  return (
    <Card className="gap-0 overflow-hidden p-0">
      <div className="px-5 py-4">
        <div className="flex items-start gap-3">
          <span className="mt-1 font-mono text-[13px] font-semibold text-primary">{route.id}</span>
          <div className="min-w-0 flex-1">
            <h3 className="font-display text-[18px] font-medium text-ink">{route.name}</h3>
            <p className="mt-1 line-clamp-2 text-[13px] leading-relaxed text-muted-foreground">
              {route.objective}
            </p>
          </div>
          {isPublished ? (
            <Badge variant="success">
              <Check className="size-3" /> Publicado
            </Badge>
          ) : (
            <Badge variant="muted">{STATUS_LABEL[status]}</Badge>
          )}
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <div className="rounded-lg bg-secondary px-3 py-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
              Módulos
            </div>
            <div className="mt-1 text-[17px] font-semibold text-ink">{route.modules.length}</div>
          </div>
          <div className="rounded-lg bg-secondary px-3 py-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
              Aprobados
            </div>
            <div className="mt-1 text-[17px] font-semibold text-ink">
              {progress.done}/{route.modules.length}
            </div>
          </div>
          <div className="rounded-lg bg-secondary px-3 py-2">
            <div className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
              Assets
            </div>
            <div className="mt-1 text-[17px] font-semibold text-ink">{assetCount}</div>
          </div>
        </div>
      </div>

      <div className="border-t border-secondary px-5 py-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <div className="text-[13px] font-semibold text-ink">Módulos del curso</div>
            <p className="mt-0.5 text-[12px] text-muted-foreground">
              Vista resumida del curso publicado, no archivos sueltos.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/ruta/${route.id}`}>
                <Eye className="size-3.5" /> Ver curso
              </Link>
            </Button>
            <Button variant="ghost" size="icon" className="size-8" onClick={() => copyToClipboard(route)} title="Copiar curso para Classroom">
              <ClipboardCopy className="size-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="size-8" onClick={() => downloadMock(route)} title="Descargar paquete del curso">
              <Download className="size-3.5" />
            </Button>
          </div>
        </div>
        <div className="grid gap-2.5">
          {route.modules.map((module) => (
            <ModuleRow key={module.id} route={route} module={module} />
          ))}
        </div>
      </div>
    </Card>
  )
}

export default function Biblioteca() {
  const [tab, setTab] = useState<'published' | 'all'>('published')
  const { routeStatusOf } = useStore()

  const published = ROUTES.filter((r) => routeStatusOf(r) === 'aprobado')
  const visible = tab === 'published' ? published : ROUTES

  return (
    <div className="mx-auto max-w-[960px]">
      <Eyebrow>Biblioteca de contenido</Eyebrow>
      <PageTitle className="text-[32px]">Cursos publicados</PageTitle>
      <PageDescription className="mb-6">
        Catálogo de cursos completos aprobados para Google Classroom. Cada curso agrupa sus módulos,
        assets y materiales de apoyo en un solo paquete.
      </PageDescription>

      <Tabs value={tab} onValueChange={(v) => setTab(v as 'all' | 'published')}>
        <div className="mb-5 flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="published">
              <Check className="size-3.5" /> Publicados
            </TabsTrigger>
            <TabsTrigger value="all">Todos los cursos</TabsTrigger>
          </TabsList>
          <span className="font-mono text-[11px] text-muted-foreground">
            {visible.length} curso{visible.length !== 1 ? 's' : ''}
          </span>
        </div>

        <TabsContent value="published" className="mt-0">
          {published.length === 0 ? (
            <Card className="py-12 text-center">
              <p className="text-muted-foreground">
                Aún no hay cursos publicados. Aprueba y publica un curso para verlo aquí.
              </p>
            </Card>
          ) : (
            <div className="flex flex-col gap-4">
              {published.map((r) => (
                <CourseLibraryCard key={r.id} route={r} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="all" className="mt-0">
          <div className="flex flex-col gap-4">
            {ROUTES.map((r) => (
              <CourseLibraryCard key={r.id} route={r} />
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <Separator className="mt-8 mb-5" />
      <div className="flex items-center gap-3 rounded-xl bg-secondary px-5 py-4">
        <ClipboardCopy className="size-4 text-primary" />
        <div>
          <div className="text-[13px] font-semibold text-ink">
            Integración con Google Classroom
          </div>
          <p className="mt-0.5 text-[12.5px] leading-relaxed text-muted-foreground">
            Usa el botón de copiar para pegar directamente el contenido en una tarea o material de
            Classroom. Los archivos descargados también son compatibles.
          </p>
        </div>
      </div>
    </div>
  )
}
