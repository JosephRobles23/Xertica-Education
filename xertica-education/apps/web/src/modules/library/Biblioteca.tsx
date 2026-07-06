'use client'

import { useState } from 'react'
import {
  BookOpen,
  Check,
  ClipboardCopy,
  Download,
  FileImage,
  FlaskConical,
  ListChecks,
  Video as VideoIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Separator } from '@/shared/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { ROUTES } from '@/shared/data/routes'
import type { ContentKind, LearningRoute } from '@/shared/lib/types'

const DOWNLOADABLE_KINDS: { kind: ContentKind; label: string; icon: typeof VideoIcon; ext: string }[] = [
  { kind: 'video', label: 'Video', icon: VideoIcon, ext: '.mp4' },
  { kind: 'infografia', label: 'Infografía', icon: FileImage, ext: '.pdf' },
  { kind: 'quiz', label: 'Quiz', icon: ListChecks, ext: '.json' },
  { kind: 'lab', label: 'Laboratorio', icon: FlaskConical, ext: '.pdf' },
  { kind: 'lesson', label: 'Lesson', icon: BookOpen, ext: '.docx' },
]

function copyToClipboard(route: LearningRoute, kind: ContentKind) {
  const label = DOWNLOADABLE_KINDS.find((k) => k.kind === kind)?.label ?? kind
  const text = `[Xertica Education] ${route.name} — ${label}\nContenido listo para importar a Google Classroom.\nRuta ${route.id} · ${route.modules.length} módulos`
  navigator.clipboard.writeText(text).then(
    () => toast.success('Copiado al portapapeles', { description: `${label} de «${route.name}» listo para Classroom.` }),
    () => toast.error('No se pudo copiar'),
  )
}

function downloadMock(route: LearningRoute, kind: ContentKind) {
  const entry = DOWNLOADABLE_KINDS.find((k) => k.kind === kind)
  toast.info('Descarga simulada', {
    description: `${entry?.label ?? kind} de «${route.name}» (${route.id}_${kind}${entry?.ext ?? ''})`,
  })
}

function RouteLibraryCard({ route }: { route: LearningRoute }) {
  const isPublished = route.status === 'aprobado'

  return (
    <Card className="gap-0 overflow-hidden p-0">
      <div className="flex items-center gap-3 px-5 py-4">
        <span className="font-mono text-[13px] font-semibold text-primary">{route.id}</span>
        <h3 className="min-w-0 flex-1 font-display text-[15.5px] font-medium text-ink truncate">
          {route.name}
        </h3>
        {isPublished ? (
          <Badge variant="success">
            <Check className="size-3" /> Publicado
          </Badge>
        ) : (
          <Badge variant="muted">{route.status}</Badge>
        )}
      </div>

      <div className="border-t border-secondary px-5 py-4">
        <div className="grid gap-2.5">
          {DOWNLOADABLE_KINDS.map(({ kind, label, icon: Icon, ext }) => {
            const hasContent = kind in route.pack
            if (!hasContent) return null

            return (
              <div
                key={kind}
                className="flex items-center gap-3 rounded-lg border-[1.5px] border-border px-3.5 py-2.5"
              >
                <Icon className="size-4 text-primary" />
                <span className="flex-1 text-[13px] font-medium text-ink">{label}</span>
                <span className="font-mono text-[10px] text-muted-foreground">{ext}</span>
                <div className="flex gap-1.5">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => copyToClipboard(route, kind)}
                    title="Copiar para Classroom"
                  >
                    <ClipboardCopy className="size-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => downloadMock(route, kind)}
                    title="Descargar"
                  >
                    <Download className="size-3.5" />
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}

export default function Biblioteca() {
  const [tab, setTab] = useState<'all' | 'published'>('all')

  const published = ROUTES.filter((r) => r.status === 'aprobado')
  const visible = tab === 'published' ? published : ROUTES

  return (
    <div className="mx-auto max-w-[960px]">
      <Eyebrow>Biblioteca de contenido</Eyebrow>
      <PageTitle className="text-[32px]">Biblioteca</PageTitle>
      <PageDescription className="mb-6">
        Todo el material generado y aprobado, listo para descargar o copiar a Google Classroom.
      </PageDescription>

      <Tabs value={tab} onValueChange={(v) => setTab(v as 'all' | 'published')}>
        <div className="mb-5 flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="all">Todas las rutas</TabsTrigger>
            <TabsTrigger value="published">
              <Check className="size-3.5" /> Publicadas
            </TabsTrigger>
          </TabsList>
          <span className="font-mono text-[11px] text-muted-foreground">
            {visible.length} ruta{visible.length !== 1 ? 's' : ''}
          </span>
        </div>

        <TabsContent value="all" className="mt-0">
          <div className="flex flex-col gap-4">
            {ROUTES.map((r) => (
              <RouteLibraryCard key={r.id} route={r} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="published" className="mt-0">
          {published.length === 0 ? (
            <Card className="py-12 text-center">
              <p className="text-muted-foreground">
                Aún no hay rutas publicadas. Aprueba y publica una ruta para verla aquí.
              </p>
            </Card>
          ) : (
            <div className="flex flex-col gap-4">
              {published.map((r) => (
                <RouteLibraryCard key={r.id} route={r} />
              ))}
            </div>
          )}
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
