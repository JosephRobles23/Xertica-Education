'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight, CheckCircle2, FileText, MonitorPlay, Search, ShieldCheck, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Checkbox } from '@/shared/ui/checkbox'
import { Label } from '@/shared/ui/label'
import { Switch } from '@/shared/ui/switch'
import { Textarea } from '@/shared/ui/textarea'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { UploadStructureDialog } from '@/modules/new-route/components/UploadStructureDialog'
import { useStore } from '@/shared/store'
import { api } from '@/shared/lib/api'
import type { Source } from '@/shared/lib/types'

interface DeepResearchResult {
  detected_tools: readonly { tool: string; vendor: string }[]
  sources: readonly Source[]
}

export default function NuevaRuta() {
  const router = useRouter()
  const {
    briefText, setBriefText,
    deepResearch, setDeepResearch,
    uploadedStructure, setUploadedStructure,
    trackJob, fetchRoutes, setActiveRouteId, replaceRouteSources,
  } = useStore()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [useAsSource, setUseAsSource] = useState(true)
  const [generating, setGenerating] = useState(false)

  const propose = async () => {
    setGenerating(true)
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
        }),
      })

      setActiveRouteId(newPath.id)

      toast.loading('Generando módulos y componentes con IA...', {
        id: toastId,
        description: 'Esto tomará unos segundos (simulando pipeline)...',
      })
      
      const genResult = await api.request<{ job_id: string }>(
        `/learning-paths/${newPath.id}/generate-structure`,
        { method: 'POST' }
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
            body: JSON.stringify({ brief: briefText }),
          },
        )
        replaceRouteSources(newPath.id, research.sources)

        const toolNames = research.detected_tools.map((tool) => tool.tool).join(', ')
        toast.loading('Fuentes candidatas listas para revisión', {
          id: toastId,
          description: `${research.sources.length} fuentes para ${toolNames || 'la ruta'}.`,
        })
      }

      await fetchRoutes()

      toast.success('Estructura generada con éxito', {
        id: toastId,
        description: deepResearch
          ? 'Revisa la estructura y las fuentes verificadas antes de aprobar.'
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
        {/* Brief */}
        <div className="flex flex-col gap-2">
          <Label htmlFor="brief">Describe la ruta o pega tu estructura</Label>
          <Textarea
            id="brief"
            rows={3}
            value={briefText}
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
        <button
          type="button"
          onClick={() => setDeepResearch(!deepResearch)}
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
        </button>

        {deepResearch && (
          <div className="rounded-xl border-[1.5px] border-primary/30 bg-primary/6 px-4 py-3.5">
            <div className="mb-3 flex flex-wrap gap-2">
              {['Nano Banana', 'Veo', 'Gemini', 'BigQuery', 'Canva'].map((tool) => (
                <span
                  key={tool}
                  className="rounded-md border border-primary/25 bg-background px-2 py-1 font-mono text-[10.5px] text-primary"
                >
                  {tool}
                </span>
              ))}
            </div>
            <div className="grid gap-2 text-[12.5px] text-muted-foreground sm:grid-cols-2">
              <div className="flex items-center gap-2">
                <Search className="size-3.5 text-primary" />
                Videos tutoriales y documentación
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-3.5 text-success" />
                Canales/dominios verificados por vendor
              </div>
            </div>
          </div>
        )}

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
