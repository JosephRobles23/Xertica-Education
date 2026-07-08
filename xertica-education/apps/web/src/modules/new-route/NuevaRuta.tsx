'use client'

import { useRef, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  FileText,
  Globe2,
  MonitorPlay,
  Sparkles,
  Upload,
  Users,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Switch } from '@/shared/ui/switch'
import { Tabs, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Textarea } from '@/shared/ui/textarea'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { UploadStructureDialog } from '@/modules/new-route/components/UploadStructureDialog'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import type { CustomerArea, CustomerContext, GoogleWorkspaceUsage } from '@/shared/lib/types'


const AREA_OPTIONS: readonly CustomerArea[] = ['RRHH', 'Finanzas', 'TI', 'Educacion', 'Salud', 'General']
const WORKSPACE_OPTIONS: readonly { value: GoogleWorkspaceUsage; label: string }[] = [
  { value: 'unknown', label: 'Inferir' },
  { value: 'yes', label: 'Usa Workspace' },
  { value: 'no', label: 'No confirmado' },
]

const CUSTOMER_STEPS = [
  { icon: Globe2, label: 'Cliente' },
  { icon: Building2, label: 'Contexto' },
  { icon: Users, label: 'Audiencia' },
] as const

const emptyToUndefined = (value: string) => {
  const trimmed = value.trim()
  return trimmed.length ? trimmed : undefined
}

const inferFromText = (text: string): Partial<CustomerContext> => {
  const normalized = text.toLowerCase()

  if (/(hospital|clinica|clinica|salud|paciente|medico|health)/.test(normalized)) {
    return { industry: 'Salud', area: 'Salud' }
  }
  if (/(universidad|colegio|escuela|estudiante|docente|educacion|education)/.test(normalized)) {
    return { industry: 'Educacion', area: 'Educacion' }
  }
  if (/(banco|finanza|financiero|contabilidad|riesgo|fintech)/.test(normalized)) {
    return { industry: 'Servicios financieros', area: 'Finanzas' }
  }
  if (/(talento|rrhh|recursos humanos|people|onboarding)/.test(normalized)) {
    return { industry: 'Servicios corporativos', area: 'RRHH' }
  }
  if (/(cloud|datos|seguridad|soporte|desarrollo|it|ti)/.test(normalized)) {
    return { industry: 'Tecnologia', area: 'TI' }
  }

  return {}
}

const inferFromUrl = (url?: string): Partial<CustomerContext> => {
  if (!url) return {}
  const normalized = url.toLowerCase()
  const inferred = inferFromText(normalized)

  if (/(edu|school|university|colegio)/.test(normalized)) {
    return { industry: 'Educacion', area: 'Educacion' }
  }
  if (/(health|salud|hospital|clinic)/.test(normalized)) {
    return { industry: 'Salud', area: 'Salud' }
  }
  if (/(bank|fin|seguros|insurance)/.test(normalized)) {
    return { industry: 'Servicios financieros', area: 'Finanzas' }
  }

  return inferred
}

const compactCustomerContext = (context: CustomerContext): CustomerContext => {
  const compacted: CustomerContext = {
    url: emptyToUndefined(context.url ?? ''),
    industry: emptyToUndefined(context.industry ?? ''),
    area: context.area,
    usesGoogleWorkspace: context.usesGoogleWorkspace,
    audienceLevel: emptyToUndefined(context.audienceLevel ?? ''),
    baseMaterialFile: context.baseMaterialFile,
    inferredFrom: context.inferredFrom?.length ? context.inferredFrom : undefined,
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
    uploadedStructure, setUploadedStructure,
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
  const [dialogOpen, setDialogOpen] = useState(false)
  // ADR-0013: múltiples documentos por ruta; todos se ingestan por default (sin checkbox).
  const [materialFiles, setMaterialFiles] = useState<File[]>([])
  const [generating, setGenerating] = useState(false)
  const [contextOpen, setContextOpen] = useState(true)
  const [contextStep, setContextStep] = useState(0)
  const baseMaterialInputRef = useRef<HTMLInputElement>(null)

  const updateCustomerContext = (patch: CustomerContext) => {
    setCustomerContext({ ...customerContext, ...patch })
  }

  const inferCustomerContext = () => {
    const fromUrl = inferFromUrl(customerContext.url)
    const fromBrief = inferFromText(briefText)
    const fromMaterial = inferFromText(customerContext.baseMaterialFile?.name ?? '')
    const inferredFrom: ('url' | 'brief' | 'material')[] = []

    if (Object.keys(fromUrl).length) inferredFrom.push('url')
    if (Object.keys(fromBrief).length) inferredFrom.push('brief')
    if (Object.keys(fromMaterial).length) inferredFrom.push('material')

    const next = {
      ...customerContext,
      ...fromBrief,
      ...fromMaterial,
      ...fromUrl,
      usesGoogleWorkspace: customerContext.usesGoogleWorkspace ?? 'unknown',
      inferredFrom: inferredFrom.length ? inferredFrom : customerContext.inferredFrom,
    }

    setCustomerContext(next)
    toast.success('Contexto inferido', {
      description: next.industry
        ? `Industria sugerida: ${next.industry}${next.area ? ` · Area: ${next.area}` : ''}`
        : 'No hay suficientes pistas todavia; puedes dejarlo opcional.',
    })
  }

  // Metadata del primer doc → customerContext.baseMaterialFile (compat: inferencia +
  // "video propio" en RouteDetail). El resto vive en la lista `materialFiles`.
  const syncPrimaryMeta = (files: File[]) => {
    const first = files[0]
    updateCustomerContext({
      baseMaterialFile: first
        ? {
            name: first.name,
            type: first.type || first.name.split('.').pop()?.toUpperCase() || 'archivo',
            sizeKb: Math.max(1, Math.round(first.size / 1024)),
          }
        : undefined,
      inferredFrom: first
        ? Array.from(new Set([...(customerContext.inferredFrom ?? []), 'material']))
        : customerContext.inferredFrom,
    })
  }

  const attachMaterial = (incoming: FileList | File[] | null) => {
    const files = incoming ? Array.from(incoming) : []
    if (!files.length) return
    // dedup por nombre+tamaño para no subir el mismo archivo dos veces.
    const merged = [...materialFiles]
    for (const f of files) {
      if (!merged.some((m) => m.name === f.name && m.size === f.size)) merged.push(f)
    }
    setMaterialFiles(merged)
    syncPrimaryMeta(merged)
    toast.success(
      files.length > 1 ? `${files.length} documentos adjuntados` : 'Documento adjuntado',
      { description: 'Se usará como contexto y se añadirá a la base de conocimiento.' },
    )
  }

  const removeMaterial = (index: number) => {
    const next = materialFiles.filter((_, i) => i !== index)
    setMaterialFiles(next)
    syncPrimaryMeta(next)
  }

  const propose = async () => {
    setGenerating(true)
    const routeCustomerContext = compactCustomerContext(customerContext)
    const toastId = toast.loading('Iniciando generación de estructura con IA...', {
      description: 'Creando ruta en el backend...',
    })

    try {
      const newPath = await api.request<{ id: string }>('/learning-paths/', {
        method: 'POST',
        body: JSON.stringify({
          titulo: 'Ruta de Inteligencia Avanzada',
          tema: 'Razonamiento',
          brief: briefText,
          customerContext: routeCustomerContext,
        }),
      })

      setActiveRouteId(newPath.id)

      // Vía 2 (ADR-0013): sube cada documento del cliente a la ruta recién creada.
      // Todos se ingestan por default (contexto de estructura + fuente de la KB).
      for (const file of materialFiles) {
        try {
          const uploaded = await api.uploadDocument(newPath.id, file)
          toast.loading('Documento subido · se añadirá a la base de conocimiento', {
            id: toastId,
            description: uploaded.filename,
          })
        } catch (uploadErr) {
          toast.error(`No se pudo subir ${file.name}`, {
            description: uploadErr instanceof Error ? uploadErr.message : 'Error desconocido',
          })
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
          body: JSON.stringify({ customerContext: routeCustomerContext }),
        }
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

  return (
    <div className="mx-auto max-w-[760px]">
      <Eyebrow tone="primary">Gate 0 · Crear ruta · Aprobación humana</Eyebrow>
      <PageTitle>Nueva ruta de aprendizaje</PageTitle>
      <PageDescription className="mb-7">
        Aporta una idea o sube tu material. La IA propone la estructura — módulos y componentes —
        y tú la curas antes de crear la ruta.
      </PageDescription>

      <Card className="gap-5 p-6">
        {/* Contexto del cliente */}
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
                Contexto del cliente
              </span>
              <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">
                Opcional. Personaliza ejemplos, labs y fuentes desde URL, brief o material base.
              </span>
            </span>
            <span className="font-mono text-[10.5px] text-muted-foreground">
              {contextOpen ? 'ocultar' : 'abrir'}
            </span>
          </button>

          {contextOpen && (
            <div className="mt-4 space-y-4">
              <Tabs
                value={`step-${contextStep}`}
                onValueChange={(value) => setContextStep(Number(value.replace('step-', '')))}
              >
                <TabsList className="grid w-full grid-cols-3 rounded-lg border-b-0 bg-secondary/60 p-1">
                  {CUSTOMER_STEPS.map((step, index) => {
                    const Icon = step.icon
                    return (
                      <TabsTrigger
                        key={step.label}
                        value={`step-${index}`}
                        className="h-8 rounded-md border-0 px-2 py-0 text-[12px] data-[state=active]:bg-card data-[state=active]:shadow-xs"
                      >
                        <Icon className="size-3.5" />
                        <span className="truncate">{step.label}</span>
                      </TabsTrigger>
                    )
                  })}
                </TabsList>
              </Tabs>

              {contextStep === 0 && (
                <div className="grid gap-3 sm:grid-cols-[1.25fr_0.75fr]">
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="customer-url">URL del cliente</Label>
                    <Input
                      id="customer-url"
                      value={customerContext.url ?? ''}
                      placeholder="https://cliente.com"
                      onChange={(e) => updateCustomerContext({ url: e.target.value })}
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="customer-industry">Industria</Label>
                    <Input
                      id="customer-industry"
                      value={customerContext.industry ?? ''}
                      placeholder="Inferida o manual"
                      onChange={(e) => updateCustomerContext({ industry: e.target.value })}
                    />
                  </div>
                </div>
              )}

              {contextStep === 1 && (
                <div className="space-y-3">
                  <div className="flex flex-col gap-2">
                    <Label>Área</Label>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {AREA_OPTIONS.map((area) => (
                        <button
                          type="button"
                          key={area}
                          onClick={() => updateCustomerContext({ area })}
                          className={`h-9 rounded-lg border-[1.5px] px-3 text-[12.5px] font-semibold transition-colors ${
                            customerContext.area === area
                              ? 'border-primary bg-primary/8 text-primary'
                              : 'border-input bg-card text-foreground hover:border-ink'
                          }`}
                        >
                          {area === 'Educacion' ? 'Educación' : area}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label>Google Workspace</Label>
                    <div className="grid gap-2 sm:grid-cols-3">
                      {WORKSPACE_OPTIONS.map((option) => (
                        <button
                          type="button"
                          key={option.value}
                          onClick={() => updateCustomerContext({ usesGoogleWorkspace: option.value })}
                          className={`h-9 rounded-lg border-[1.5px] px-3 text-[12.5px] font-semibold transition-colors ${
                            (customerContext.usesGoogleWorkspace ?? 'unknown') === option.value
                              ? 'border-primary bg-primary/8 text-primary'
                              : 'border-input bg-card text-foreground hover:border-ink'
                          }`}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {contextStep === 2 && (
                <div className="space-y-3">
                  <div className="flex flex-col gap-2">
                    <Label htmlFor="audience-level">Audiencia / nivel</Label>
                    <Input
                      id="audience-level"
                      value={customerContext.audienceLevel ?? ''}
                      placeholder="Ej. líderes no técnicos, analistas, docentes"
                      onChange={(e) => updateCustomerContext({ audienceLevel: e.target.value })}
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <Label>Propuesta del cliente</Label>
                    <button
                      type="button"
                      onClick={() => baseMaterialInputRef.current?.click()}
                      className="w-full cursor-pointer rounded-xl border-[1.5px] border-dashed border-input bg-background/60 p-5 text-center transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
                    >
                      <Upload className="mx-auto mb-1.5 size-5 text-muted-foreground" />
                      <div className="text-[13px]">Adjunta propuesta, temario o material base</div>
                      <div className="mt-1 font-mono text-[10.5px] text-muted-foreground">
                        DOCX · PDF · PPTX · XLSX · TXT
                      </div>
                    </button>
                    {customerContext.baseMaterialFile && (
                      <div className="flex items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5">
                        <FileText className="size-4 shrink-0 text-primary" />
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-[13px] text-ink">
                            {customerContext.baseMaterialFile.name}
                          </div>
                          <div className="font-mono text-[10.5px] text-muted-foreground">
                            {customerContext.baseMaterialFile.sizeKb} KB · propuesta del cliente
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-7"
                          onClick={() => {
                            setMaterialFiles([])
                            updateCustomerContext({ baseMaterialFile: undefined })
                          }}
                        >
                          <X className="size-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2 border-t-[1.5px] border-border pt-3">
                <Button type="button" variant="outline-primary" size="sm" onClick={inferCustomerContext}>
                  <Sparkles /> Inferir contexto
                </Button>
                {([
                  customerContext.industry,
                  customerContext.area === 'Educacion' ? 'Educación' : customerContext.area,
                  customerContext.usesGoogleWorkspace === 'yes' ? 'Google Workspace' : undefined,
                  customerContext.audienceLevel,
                ].filter(Boolean) as string[]).map((item) => (
                  <span
                    key={item}
                    className="rounded-md border border-primary/25 bg-primary/6 px-2 py-1 font-mono text-[10.5px] text-primary"
                  >
                    {item}
                  </span>
                ))}
                {!customerContext.industry && !customerContext.area && !customerContext.audienceLevel && (
                  <span className="font-mono text-[10.5px] text-muted-foreground">
                    La ruta puede generarse sin completar este bloque.
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Brief */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="brief">Describe el objetivo de aprendizaje</Label>
          <Textarea
            id="brief"
            rows={4}
            value={briefText}
            placeholder={'Objetivo de aprendizaje: ¿qué quieres enseñar y por qué?\n\nIncluye, si lo tienes: nombre de la ruta, herramientas o habilidades a enseñar, puntos importantes a tratar y casos de uso.'}
            onChange={(e) => setBriefText(e.target.value)}
          />
        </div>

        {/* Upload estructura */}
        <div className="flex flex-col gap-2">
          <Label>Estructura de la ruta de aprendizaje</Label>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline-primary" onClick={() => setDialogOpen(true)}>
              <Upload /> Subir estructura propuesta
            </Button>
            {uploadedStructure ? (
              <span className="inline-flex items-center gap-2 rounded-full border-[1.5px] border-success bg-success/10 py-1.5 pr-2 pl-3 text-[12.5px]">
                <CheckCircle2 className="size-3.5 text-success" />
                {uploadedStructure.name} · {uploadedStructure.kind}
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-5 rounded-full"
                  onClick={() => setUploadedStructure(null)}
                >
                  <X className="size-3" />
                </Button>
              </span>
            ) : (
              <span className="font-mono text-[11px] text-muted-foreground">
                Sube DOCX, PDF o pega el texto de tu estructura.
              </span>
            )}
          </div>
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
              Agente de deep research · herramientas y fuentes verificadas
            </span>
            <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">
              Detecta herramientas como Nano Banana, Veo, Gemini o Canva y propone videos,
              documentación y referencias desde fuentes permitidas por vendor.
            </span>
          </span>
          <Switch checked={deepResearch} className="pointer-events-none" tabIndex={-1} />
        </div>

        {/* Material de referencia (Vía 2 · ADR-0013) — múltiples docs; todos a la KB por default */}
        <div className="flex flex-col gap-2">
          <Label>O sube material de referencia</Label>
          <input
            ref={baseMaterialInputRef}
            type="file"
            multiple
            accept=".docx,.pdf,.pptx,.xlsx,.txt,.md"
            className="hidden"
            onClick={(e) => {
              ;(e.currentTarget as HTMLInputElement).value = ''
            }}
            onChange={(e) => attachMaterial(e.target.files)}
          />
          <button
            type="button"
            onClick={() => baseMaterialInputRef.current?.click()}
            className="w-full cursor-pointer rounded-xl border-[1.5px] border-dashed border-input bg-background/60 p-5 text-center transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
          >
            <Upload className="mx-auto mb-1.5 size-5 text-muted-foreground" />
            <div className="text-[13px]">Selecciona uno o varios archivos</div>
            <div className="mt-1 font-mono text-[10.5px] text-muted-foreground">
              DOCX · PDF · PPTX · XLSX · TXT
            </div>
          </button>
          {materialFiles.length > 0 ? (
            <div className="flex flex-col gap-2">
              {materialFiles.map((file, index) => (
                <div
                  key={`${file.name}-${file.size}`}
                  className="flex items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5"
                >
                  <FileText className="size-4 shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] text-ink">{file.name}</div>
                    <div className="font-mono text-[10.5px] text-muted-foreground">
                      {Math.max(1, Math.round(file.size / 1024))} KB · contexto + fuente de la KB
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-7"
                    onClick={() => removeMaterial(index)}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <span className="font-mono text-[11px] text-muted-foreground">
              Adjunta uno o varios archivos: informan la estructura y alimentan la base de conocimiento.
            </span>
          )}
        </div>

        <Button className="w-full" onClick={propose} disabled={generating}>
          {generating ? 'Generando estructura...' : 'Proponer estructura con IA'} <ArrowRight />
        </Button>
      </Card>

      <UploadStructureDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={setUploadedStructure}
      />
    </div>
  )
}
