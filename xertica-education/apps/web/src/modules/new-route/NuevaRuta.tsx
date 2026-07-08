'use client'

import { useRef, useState } from 'react'
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
import { Checkbox } from '@/shared/ui/checkbox'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Switch } from '@/shared/ui/switch'
import { Tabs, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Textarea } from '@/shared/ui/textarea'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { UploadStructureDialog } from '@/modules/new-route/components/UploadStructureDialog'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import type { CustomerArea, CustomerContext, GoogleWorkspaceUsage, Source } from '@/shared/lib/types'

interface DeepResearchResult {
  detected_tools: readonly { tool: string; vendor: string }[]
  sources: readonly Source[]
}

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
    trackJob, fetchRoutes, setActiveRouteId, replaceRouteSources,
  } = useStore()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [useAsSource, setUseAsSource] = useState(true)
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

  const attachBaseMaterial = (file: File | null) => {
    if (!file) return

    updateCustomerContext({
      baseMaterialFile: {
        name: file.name,
        type: file.type || file.name.split('.').pop()?.toUpperCase() || 'archivo',
        sizeKb: Math.max(1, Math.round(file.size / 1024)),
      },
      inferredFrom: Array.from(new Set([...(customerContext.inferredFrom ?? []), 'material'])),
    })

    toast.success('Material base adjuntado', {
      description: `${file.name} se usará como contexto de personalización.`,
    })
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

      toast.loading('Generando módulos y componentes con IA...', {
        id: toastId,
        description: 'Esto tomará unos segundos (simulando pipeline)...',
      })
      
      const genResult = await api.request<{ job_id: string }>(
        `/learning-paths/${newPath.id}/generate-structure`,
        {
          method: 'POST',
          body: JSON.stringify({ customerContext: routeCustomerContext }),
        }
      )

      await trackJob(genResult.job_id)

      if (deepResearch) {
        toast.loading('Investigando fuentes verificadas...', {
          id: toastId,
          description: 'Detectando herramientas, canales oficiales y documentación relevante.',
        })

        const research = await api.request<DeepResearchResult>(
          `/learning-paths/${newPath.id}/deep-research`,
          {
            method: 'POST',
            body: JSON.stringify({ brief: briefText, customerContext: routeCustomerContext }),
          },
        )
        replaceRouteSources(newPath.id, research.sources)

        const toolNames = research.detected_tools.map((tool) => tool.tool).join(', ')
        toast.loading('Deep Research listo para enriquecer los assets', {
          id: toastId,
          description: `${research.sources.length} recomendaciones para ${toolNames || 'la ruta'}.`,
        })
      }

      await fetchRoutes()

      toast.success('Estructura generada con éxito', {
        id: toastId,
        description: deepResearch
          ? 'Revisa la estructura; las recomendaciones aparecerán dentro de cada asset relevante.'
          : 'Revisa, reordena y cura los módulos antes de aprobar.',
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
                    <input
                      ref={baseMaterialInputRef}
                      type="file"
                      accept=".doc,.docx,.pdf,.ppt,.pptx,.xls,.xlsx,.txt,.md"
                      className="hidden"
                      onChange={(e) => attachBaseMaterial(e.target.files?.[0] ?? null)}
                    />
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
                          onClick={() => updateCustomerContext({ baseMaterialFile: undefined })}
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

        {/* Material de referencia */}
        <div className="flex flex-col gap-2">
          <Label>O sube material de referencia</Label>
          <div className="rounded-xl border-[1.5px] border-dashed border-input bg-background/60 p-5 text-center">
            <Upload className="mx-auto mb-1.5 size-5 text-muted-foreground" />
            <div className="text-[13px]">Arrastra o selecciona archivos</div>
            <div className="mt-1 font-mono text-[10.5px] text-muted-foreground">
              DOCX · PDF · PPTX — se parsean con MinerU
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5">
            <FileText className="size-4 text-primary" />
            <div className="min-w-0 flex-1">
              <div className="text-[13px] text-ink">temario-ia-avanzada.docx</div>
              <div className="font-mono text-[10.5px] text-muted-foreground">214 KB · procesado</div>
            </div>
            <Label htmlFor="use-source" className="cursor-pointer gap-2 font-normal text-foreground">
              <Checkbox
                id="use-source"
                checked={useAsSource}
                onCheckedChange={(v) => setUseAsSource(v === true)}
              />
              <span className="text-xs">usar también como fuente</span>
            </Label>
          </div>
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
