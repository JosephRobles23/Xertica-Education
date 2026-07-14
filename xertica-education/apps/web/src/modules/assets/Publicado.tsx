'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Check, CircleCheck, ExternalLink, FolderUp } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { PageTitle } from '@/shared/components/PageHeader'
import { getRoute } from '@/shared/data/routes'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import { authorizeGoogleDrive } from '@/shared/lib/googleDrive'

export default function Publicado() {
  const { id } = useParams<{ id: string }>()
  const { routes } = useStore()
  const route = routes.find((item) => item.id === id) ?? getRoute(id)
  const [savingDrive, setSavingDrive] = useState(false)
  const [driveLink, setDriveLink] = useState<string | null>(null)

  const saveAllToDrive = async () => {
    if (!route) return
    setSavingDrive(true)
    const toastId = toast.loading('Guardando paquete completo en Google Drive...')
    try {
      const accessToken = await authorizeGoogleDrive()
      const uploaded = await api.saveRouteBundleToGoogleDrive(
        route.id,
        accessToken,
        `${route.name || route.id} - assets.zip`,
      )
      setDriveLink(uploaded.web_view_link ?? null)
      toast.success('Paquete guardado en Google Drive', {
        id: toastId,
        description: `${uploaded.name}${uploaded.included_count !== undefined ? ` · ${uploaded.included_count} archivos` : ''}`,
      })
    } catch (error) {
      toast.error('No se pudo guardar en Drive', {
        id: toastId,
        description: error instanceof Error ? error.message : 'Error desconocido',
      })
    } finally {
      setSavingDrive(false)
    }
  }

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
        El contenido de «{route.name}» se publicó a Classroom. Las inscripciones y el seguimiento
        continúan en Classroom — Xertica entrega el contenido, no lo administra.
      </p>

      <Card className="mb-6 flex-row items-center gap-3 border-success bg-success/10 p-4.5 text-left">
        <CircleCheck className="size-4 shrink-0 text-success" />
        <span className="text-[13.5px] leading-relaxed">
          Publicado <b className="text-ink">· {route.name}</b> 
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

      <div className="flex flex-wrap justify-center gap-3">
        {driveLink ? (
          <Button variant="outline-primary" asChild>
            <a href={driveLink} target="_blank" rel="noreferrer">
              <ExternalLink /> Abrir en Drive
            </a>
          </Button>
        ) : null}
        <Button variant="outline-primary" onClick={saveAllToDrive} disabled={savingDrive}>
          <FolderUp /> {savingDrive ? 'Guardando...' : 'Save all to Google Drive'}
        </Button>
        <Button asChild>
          <Link href={`/ruta/${route.id}`}>Volver a la ruta</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/">Ver todas las rutas</Link>
        </Button>
      </div>
    </div>
  )
}
