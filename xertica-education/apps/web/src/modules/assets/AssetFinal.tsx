'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useState } from 'react'
import { ArrowRight, CircleCheck, ExternalLink, FileImage, FlaskConical, FolderUp, ListChecks, RefreshCcw, ShieldCheck, Video as VideoIcon, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Separator } from '@/shared/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { VideoFrame } from '@/shared/content/VideoFrame'
import { InfografiaView } from '@/shared/content/InfografiaView'
import { QuizView } from '@/shared/content/QuizView'
import { LabView } from '@/shared/content/LabView'
import { getRoute } from '@/shared/data/routes'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import { authorizeGoogleDrive } from '@/shared/lib/googleDrive'

export default function AssetFinal() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { routes, storyboardVideoUrlOf } = useStore()
  const route = routes.find((item) => item.id === id) ?? getRoute(id)
  const videoUrl = route ? storyboardVideoUrlOf(route.id) : ''
  const [savingDrive, setSavingDrive] = useState(false)
  const [driveLink, setDriveLink] = useState<string | null>(null)

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
    toast.success('Asset aprobado', { description: 'Publicando a Google Classroom…' })
    router.push(`/ruta/${route.id}/publicado`)
  }

  const saveToDrive = async () => {
    if (!route) return
    setSavingDrive(true)
    const toastId = toast.loading('Guardando asset final en Google Drive...')
    try {
      const accessToken = await authorizeGoogleDrive()
      const uploaded = await api.saveRouteToGoogleDrive(
        route.id,
        accessToken,
        `${route.name || route.id} - asset final.md`,
      )
      setDriveLink(uploaded.web_view_link ?? null)
      toast.success('Asset guardado en Google Drive', {
        id: toastId,
        description: uploaded.name,
      })
    } catch (err) {
      toast.error('No se pudo guardar en Drive', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    } finally {
      setSavingDrive(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-[1120px] items-start gap-8 lg:grid-cols-[1fr_288px]">
      <div>
        <Eyebrow tone="primary">
          Ruta {route.id} · Revisión final · Aprobación humana
        </Eyebrow>
        <PageTitle>Revisar asset final</PageTitle>
        <PageDescription className="mb-5">
          El material de todos los módulos fue generado. Revisa cada formato antes de publicar a
          Classroom.
        </PageDescription>

        <Tabs defaultValue="video">
          <TabsList className="mb-5">
            <TabsTrigger value="video">
              <VideoIcon /> Video
            </TabsTrigger>
            <TabsTrigger value="infografia">
              <FileImage /> Infografía
            </TabsTrigger>
            <TabsTrigger value="quiz">
              <ListChecks /> Quiz
            </TabsTrigger>
            <TabsTrigger value="lab">
              <FlaskConical /> Laboratorio
            </TabsTrigger>
          </TabsList>

          <TabsContent value="video">
            <VideoFrame video={route.pack.video} videoUrl={videoUrl} />
          </TabsContent>
          <TabsContent value="infografia">
            <InfografiaView info={route.pack.infografia} routeId={route.id} />
          </TabsContent>
          <TabsContent value="quiz">
            <QuizView quiz={route.pack.quiz} />
          </TabsContent>
          <TabsContent value="lab">
            <LabView lab={route.pack.lab} />
          </TabsContent>
        </Tabs>

        <Separator className="mt-7 mb-5" />
        <div className="flex items-center justify-end gap-3">
          {driveLink && (
            <Button variant="outline-primary" asChild>
              <a href={driveLink} target="_blank" rel="noreferrer">
                <ExternalLink /> Open in Drive
              </a>
            </Button>
          )}
          <Button variant="outline-primary" onClick={saveToDrive} disabled={savingDrive}>
            <FolderUp /> {savingDrive ? 'Guardando...' : 'Save to Google Drive'}
          </Button>
          <Button
            variant="outline-destructive"
            onClick={() => toast.error('Asset rechazado', { description: 'El pipeline volverá a la etapa de generación.' })}
          >
            <X /> Rechazar
          </Button>
          <Button
            variant="outline"
            onClick={() => toast.info('Generando nueva versión…', { description: 'Se conservará la versión actual como referencia.' })}
          >
            <RefreshCcw /> Nueva versión
          </Button>
          <Button variant="success" onClick={approve}>
            <CircleCheck /> Aprobar <ArrowRight /> Classroom
          </Button>
        </div>
      </div>

      {/* Provenance del asset */}
      <Card className="sticky top-20 gap-4 p-5">
        <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          Provenance · Asset
        </div>
        <div>
          <div className="mb-1 text-[11px] text-muted-foreground">Modelos usados</div>
          <div className="font-mono text-[13px] leading-relaxed text-ink">
            Gemini 2.5 · guion
            <br />
            Veo 3 · render
          </div>
        </div>
        <Separator className="bg-secondary" />
        <div>
          <div className="mb-2.5 text-[11px] text-muted-foreground">Fuentes citadas</div>
          <div className="flex flex-col gap-2.5">
            {route.sources
              .filter((f) => f.verified)
              .map((f) => (
                <div key={f.title} className="flex items-start gap-2">
                  <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-success/12">
                    <ShieldCheck className="size-2.5 text-success" />
                  </span>
                  <span className="text-[11.5px] leading-snug">{f.title}</span>
                </div>
              ))}
          </div>
        </div>
      </Card>
    </div>
  )
}
