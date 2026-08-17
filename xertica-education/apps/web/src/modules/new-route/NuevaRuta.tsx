'use client'

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowRight,
  FileText,
  FolderOpen,
  ListTree,
  MonitorPlay,
  Sparkles,
  Upload,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Switch } from '@/shared/ui/switch'
import { Textarea } from '@/shared/ui/textarea'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import { pickGoogleDriveFile } from '@/shared/lib/googleDrive'
import type { GoogleDriveSelection } from '@/shared/lib/googleDrive'
import type { CustomerContext } from '@/shared/lib/types'

/** Sugerencias de área. El campo es texto libre (ADR-0024): la ruta puede ser de cualquier ámbito. */
const AREA_SUGGESTIONS = ['RRHH', 'Finanzas', 'TI', 'Educación', 'Salud', 'Ventas', 'Operaciones', 'Legal']

/** Líneas que delatan un temario ya redactado: headers, "Módulo 3", "Lección 2.1", "1. …". */
const STRUCTURE_LINE = /^\s*(#{1,4}\s|m[óo]dulo\s+\d|lecci[óo]n\s+\d|unidad\s+\d|tema\s+\d|\d+[.)]\s)/i
/** Solo lo que se lee como un módulo/unidad de primer nivel, para estimar el tamaño. */
const MODULE_LINE = /^\s*(#{1,2}\s|m[óo]dulo\s+\d|unidad\s+\d)/i

/** Heurística local (sin LLM): ¿el usuario pegó una estructura o solo un objetivo? */
export const detectStructureHint = (text: string): { hasStructure: boolean; modules: number } => {
  const lines = text.split('\n')
  const structured = lines.filter((line) => STRUCTURE_LINE.test(line))
  if (structured.length < 3) return { hasStructure: false, modules: 0 }
  const modules = lines.filter((line) => MODULE_LINE.test(line)).length
  return { hasStructure: true, modules: modules || structured.length }
}

const emptyToUndefined = (value: string) => {
  const trimmed = value.trim()
  return trimmed.length ? trimmed : undefined
}

const fileMetaOf = (file: GoogleDriveSelection | File) =>
  'file_id' in file
    ? {
        name: file.name,
        type: file.mime_type,
        sizeKb: 1,
      }
    : {
        name: file.name,
        type: file.type || 'application/octet-stream',
        sizeKb: Math.max(1, Math.round(file.size / 1024)),
      }

const compactCustomerContext = (context: CustomerContext): CustomerContext => {
  const compacted: CustomerContext = {
    industry: emptyToUndefined(context.industry ?? ''),
    area: emptyToUndefined(context.area ?? ''),
    audienceLevel: emptyToUndefined(context.audienceLevel ?? ''),
    baseMaterialFile: context.baseMaterialFile,
    companyName: emptyToUndefined(context.companyName ?? ''),
  }

  return Object.fromEntries(
    Object.entries(compacted).filter(([, value]) => value !== undefined),
  ) as CustomerContext
}

export default function NuevaRuta() {
  const router = useRouter()
  const {
    briefText, setBriefText,
    deepResearch, setDeepResearch,
    customerContext, setCustomerContext,
    fetchRoutes, setActiveRouteId,
    setStructureJobId, setPendingDeepResearch,
    setProposalLoadedRouteId, setProposal,
  } = useStore()

  useEffect(() => {
    // Reset any previous active route details and proposal on mount
    setActiveRouteId(null)
    setStructureJobId(null)
    setPendingDeepResearch(false)
    setProposalLoadedRouteId(null)
    setProposal([])
  }, [setActiveRouteId, setStructureJobId, setPendingDeepResearch, setProposalLoadedRouteId, setProposal])

  // ADR-0013: múltiples documentos por ruta; todos se ingestan por default (sin checkbox).
  // Una sola zona de material (ADR-0024): estructura, propuesta y referencias van al mismo sitio.
  const [driveFiles, setDriveFiles] = useState<GoogleDriveSelection[]>([])
  const [localFiles, setLocalFiles] = useState<File[]>([])
  const [generating, setGenerating] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const materialFileInputRef = useRef<HTMLInputElement | null>(null)

  const structureHint = useMemo(() => detectStructureHint(briefText), [briefText])
  const hasMaterial = driveFiles.length > 0 || localFiles.length > 0

  const updateCustomerContext = (patch: CustomerContext) => {
    setCustomerContext({ ...customerContext, ...patch })
  }

  // Metadata del primer doc → customerContext.baseMaterialFile (lo usa "video propio"
  // en RouteDetail). El resto vive en las listas `driveFiles` / `localFiles`.
  const syncPrimaryMeta = (driveSelections: GoogleDriveSelection[], localSelections: File[]) => {
    const first = driveSelections[0] ?? localSelections[0]
    updateCustomerContext({ baseMaterialFile: first ? fileMetaOf(first) : undefined })
  }

  const attachDriveMaterial = async () => {
    try {
      const selected = await pickGoogleDriveFile()
      if (!selected) return
      const next = driveFiles.some((file) => file?.file_id === selected.file_id)
        ? driveFiles
        : [...driveFiles, selected]
      setDriveFiles(next)
      syncPrimaryMeta(next, localFiles)
      toast.success('Archivo de Drive seleccionado', { description: selected.name })
    } catch (err) {
      toast.error('No se pudo abrir Google Drive', {
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    }
  }

  const removeDriveMaterial = (index: number) => {
    const next = driveFiles.filter((_, i) => i !== index)
    setDriveFiles(next)
    syncPrimaryMeta(next, localFiles)
  }

  const attachLocalMaterial = () => {
    materialFileInputRef.current?.click()
  }

  const onLocalMaterialSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    const next = localFiles.some(
      (item) => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified,
    )
      ? localFiles
      : [...localFiles, file]
    setLocalFiles(next)
    syncPrimaryMeta(driveFiles, next)
    toast.success('Archivo local seleccionado', { description: file.name })
  }

  const removeLocalMaterial = (index: number) => {
    const next = localFiles.filter((_, i) => i !== index)
    setLocalFiles(next)
    syncPrimaryMeta(driveFiles, next)
  }

  const propose = async () => {
    setGenerating(true)
    const routeCustomerContext = compactCustomerContext(customerContext)
    const toastId = toast.loading('Iniciando generación de estructura con IA...', {
      description: 'Creando ruta en el backend...',
    })

    try {
      // Título/tema provisionales derivados del brief; la IA (generate-structure)
      // los reemplaza con un nombre y tema definitivos al completar el Job.
      const provisionalTitle =
        (briefText.trim().split('\n')[0] ?? '').trim().slice(0, 60) || 'Nueva ruta de aprendizaje'
      const newPath = await api.request<{ id: string }>('/learning-paths/', {
        method: 'POST',
        body: JSON.stringify({
          titulo: provisionalTitle,
          tema: '',
          brief: briefText,
          customerContext: routeCustomerContext,
        }),
      })

      setActiveRouteId(newPath.id)

      // Vía 2 (ADR-0013): importa cada documento de apoyo a la ruta recién creada.
      // Todos se ingestan por default (contexto de estructura + fuente de la KB).
      for (const file of driveFiles) {
        try {
          const uploaded = await api.uploadDriveDocument(newPath.id, file)
          toast.loading('Documento de Drive importado · se añadirá a la base de conocimiento', {
            id: toastId,
            description: uploaded.filename,
          })
        } catch (uploadErr) {
          const message = uploadErr instanceof Error ? uploadErr.message : 'Error desconocido'
          toast.error(`No se pudo importar ${file.name}`, { id: toastId, description: message })
          throw new Error(`No se pudo importar ${file.name}: ${message}`)
        }
      }

      for (const file of localFiles) {
        try {
          const uploaded = await api.uploadDocument(newPath.id, file)
          toast.loading('Documento local importado · se añadirá a la base de conocimiento', {
            id: toastId,
            description: uploaded.filename,
          })
        } catch (uploadErr) {
          const message = uploadErr instanceof Error ? uploadErr.message : 'Error desconocido'
          toast.error(`No se pudo importar ${file.name}`, { id: toastId, description: message })
          throw new Error(`No se pudo importar ${file.name}: ${message}`)
        }
      }

      toast.loading('Iniciando generación de estructura con IA...', {
        id: toastId,
        description: 'Preparando Job en background...',
      })

      const genResult = await api.request<{ job_id: string }>(
        `/learning-paths/${newPath.id}/generate-structure`,
        {
          method: 'POST',
          body: JSON.stringify({
            brief: briefText,
            customerContext: routeCustomerContext,
          }),
        },
      )

      setStructureJobId(genResult.job_id)
      setPendingDeepResearch(deepResearch)

      await fetchRoutes()

      toast.success('Generación curricular en curso', {
        id: toastId,
        description: 'Serás redirigido para observar el progreso en tiempo real.',
      })
      router.push('/estructura-propuesta')
    } catch (err) {
      console.error(err)
      toast.error('Error al generar la estructura', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    } finally {
      setGenerating(false)
    }
  }

  const contextChips = [
    customerContext.companyName,
    customerContext.industry,
    customerContext.area,
    customerContext.audienceLevel,
  ].filter(Boolean) as string[]

  return (
    <div className="mx-auto max-w-[760px]">
      <Eyebrow tone="primary">Gate 0 · Crear ruta · Aprobación humana</Eyebrow>
      <PageTitle>Nueva ruta de aprendizaje</PageTitle>
      <PageDescription className="mb-7">
        Describe tu objetivo o pega la estructura que ya tengas. La IA propone los módulos y
        componentes, y tú los curas antes de crear la ruta.
      </PageDescription>

      <Card className="gap-6 p-6">
        {/* Hero · brief unificado (objetivo y/o estructura · ADR-0024) */}
        <div className="flex flex-col gap-2.5">
          <Label htmlFor="brief" className="text-[14px]">
            ¿Qué quieres enseñar?
          </Label>
          <Textarea
            id="brief"
            rows={10}
            value={briefText}
            className="resize-y text-[14px] leading-relaxed"
            placeholder={
              'Escribe el objetivo de aprendizaje, o pega directamente tu estructura de curso.\n\n' +
              'Por ejemplo:\n' +
              '· "Quiero enseñar atención al cliente con empatía a recepcionistas de veterinarias."\n' +
              '· O tu temario completo: Módulo 1 · … / Lección 1.1 · …\n\n' +
              'Si pegas una estructura, la respetamos tal cual; si no, te proponemos una.'
            }
            onChange={(e) => setBriefText(e.target.value)}
          />
          {structureHint.hasStructure && (
            <div className="flex items-center gap-2 rounded-lg border-[1.5px] border-success/30 bg-success/8 px-3 py-2">
              <ListTree className="size-4 shrink-0 text-success" />
              <span className="text-[12.5px] text-ink">
                Estructura detectada
                {structureHint.modules > 0 && ` · ~${structureHint.modules} módulos`} — la
                respetaremos como esqueleto de la ruta.
              </span>
            </div>
          )}
        </div>

        {/* Material de apoyo · una sola zona (ADR-0024) */}
        <div className="flex flex-col gap-2">
          <Label>Material de apoyo (opcional)</Label>
          <div className="grid gap-2 sm:grid-cols-2">
            <button
              type="button"
              onClick={attachDriveMaterial}
              className="w-full cursor-pointer rounded-xl border-[1.5px] border-dashed border-input bg-background/60 p-5 text-center transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
            >
              <FolderOpen className="mx-auto mb-1.5 size-5 text-muted-foreground" />
              <div className="text-[13px]">Seleccionar desde Google Drive</div>
              <div className="mt-1 font-mono text-[10.5px] text-muted-foreground">
                DOCX · PDF · PPTX · XLSX · TXT
              </div>
            </button>
            <button
              type="button"
              onClick={attachLocalMaterial}
              className="w-full cursor-pointer rounded-xl border-[1.5px] border-dashed border-input bg-background/60 p-5 text-center transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
            >
              <Upload className="mx-auto mb-1.5 size-5 text-muted-foreground" />
              <div className="text-[13px]">Subir desde tu computador</div>
              <div className="mt-1 font-mono text-[10.5px] text-muted-foreground">
                DOCX · PDF · PPTX · XLSX · TXT
              </div>
            </button>
          </div>
          {hasMaterial ? (
            <div className="flex flex-col gap-2">
              {driveFiles.map((file, index) => (
                <div
                  key={file.file_id}
                  className="flex items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5"
                >
                  <FileText className="size-4 shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] text-ink">{file.name}</div>
                    <div className="font-mono text-[10.5px] text-muted-foreground">
                      Google Drive · contexto + fuente de la KB
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => removeDriveMaterial(index)}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              ))}
              {localFiles.map((file, index) => (
                <div
                  key={`${file.name}-${file.size}-${file.lastModified}`}
                  className="flex items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5"
                >
                  <FileText className="size-4 shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] text-ink">{file.name}</div>
                    <div className="font-mono text-[10.5px] text-muted-foreground">
                      Computador · contexto + fuente de la KB
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => removeLocalMaterial(index)}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <span className="font-mono text-[11px] text-muted-foreground">
              Temario, syllabus, presentaciones o cualquier documento base: informan la estructura
              y alimentan la base de conocimiento.
            </span>
          )}
        </div>

        {/* Contexto de la compañía · 4 campos, colapsable (ADR-0024) */}
        <div className="rounded-xl border-[1.5px] border-input bg-background/70 p-4">
          <button
            type="button"
            onClick={() => setContextOpen(!contextOpen)}
            className="flex w-full items-center gap-3 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30"
          >
            <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10">
              <Sparkles className="size-4.5 text-primary" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[13.5px] font-semibold text-ink">
                Contexto de la compañía
              </span>
              <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">
                Opcional. Personaliza ejemplos, labs y el tono de la ruta.
              </span>
            </span>
            {!contextOpen && contextChips.length > 0 && (
              <span className="hidden max-w-[45%] truncate font-mono text-[10.5px] text-primary sm:block">
                {contextChips.join(' · ')}
              </span>
            )}
            <span className="font-mono text-[10.5px] text-muted-foreground">
              {contextOpen ? 'ocultar' : 'abrir'}
            </span>
          </button>

          {contextOpen && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label htmlFor="customer-company">Empresa</Label>
                <Input
                  id="customer-company"
                  value={customerContext.companyName ?? ''}
                  placeholder="Nombre del cliente"
                  onChange={(e) => updateCustomerContext({ companyName: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="customer-industry">Industria</Label>
                <Input
                  id="customer-industry"
                  value={customerContext.industry ?? ''}
                  placeholder="Ej. retail, minería, salud"
                  onChange={(e) => updateCustomerContext({ industry: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="audience-level">Audiencia / nivel</Label>
                <Input
                  id="audience-level"
                  value={customerContext.audienceLevel ?? ''}
                  placeholder="Ej. líderes no técnicos, analistas"
                  onChange={(e) => updateCustomerContext({ audienceLevel: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="customer-area">Área</Label>
                <Input
                  id="customer-area"
                  value={customerContext.area ?? ''}
                  placeholder="Cualquier área"
                  onChange={(e) => updateCustomerContext({ area: e.target.value })}
                />
                <div className="flex flex-wrap gap-1.5">
                  {AREA_SUGGESTIONS.map((area) => (
                    <button
                      type="button"
                      key={area}
                      onClick={() => updateCustomerContext({ area })}
                      className={`h-7 rounded-md border px-2 text-[11.5px] font-medium transition-colors ${
                        customerContext.area === area
                          ? 'border-primary bg-primary/8 text-primary'
                          : 'border-input bg-card text-muted-foreground hover:border-ink hover:text-ink'
                      }`}
                    >
                      {area}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Deep research */}
        <div
          role="switch"
          aria-checked={deepResearch}
          tabIndex={0}
          onClick={() => setDeepResearch(!deepResearch)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              setDeepResearch(!deepResearch)
            }
          }}
          className={`flex cursor-pointer items-center gap-3.5 rounded-xl border-[1.5px] p-4 text-left transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30 ${
            deepResearch ? 'border-primary bg-primary/8' : 'border-border bg-background/60 hover:border-input'
          }`}
        >
          <span className="flex size-9 items-center justify-center rounded-lg bg-destructive/10">
            <MonitorPlay className="size-4.5 text-destructive" />
          </span>
          <span className="flex-1">
            <span className="block text-[13.5px] font-semibold text-ink">
              Agente de deep research · fuentes verificadas
            </span>
            <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">
              Detecta las herramientas que menciones y propone videos, documentación y referencias
              desde sus fuentes oficiales.
            </span>
          </span>
          <Switch checked={deepResearch} className="pointer-events-none" tabIndex={-1} />
        </div>

        <Button className="w-full" onClick={propose} disabled={generating || !briefText.trim()}>
          {generating ? 'Generando estructura...' : 'Proponer estructura con IA'} <ArrowRight />
        </Button>
      </Card>

      <input
        ref={materialFileInputRef}
        type="file"
        accept=".doc,.docx,.pdf,.ppt,.pptx,.xls,.xlsx,.txt"
        className="hidden"
        onChange={onLocalMaterialSelected}
      />
    </div>
  )
}
