'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  CircleCheck,
  Clapperboard,
  ExternalLink,
  FileText,
  FlaskConical,
  Info,
  Loader2,
  Play,
  Search,
  ShieldCheck,
  Sparkles,
  Wand2,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Separator } from '@/shared/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'
import { Eyebrow, PageTitle } from '@/shared/components/PageHeader'
import { StatusBadge } from '@/shared/content/StatusBadge'
import { ContentPreview } from '@/shared/content/ContentPreview'
import { SourceVideoPreview } from '@/shared/content/SourceVideoPreview'
import { RefinePopover } from '@/modules/routes/components/RefinePopover'
import {
  KIND_LABEL,
  type LearningRoute,
  type ModuleContentRef,
  type RouteModule,
  type Source,
} from '@/shared/lib/types'
import { useStore } from '@/shared/store'
import { cn } from '@/shared/lib/utils'

/* ── Fuente individual (con preview de video colapsable) ───────── */
function SourceCard({
  source,
  approved,
  onDiscard,
}: {
  source: Source
  approved: boolean
  onDiscard: () => void
}) {
  const [videoOpen, setVideoOpen] = useState(false)
  const requiresReview = source.status === 'requires-review' || !source.verified

  return (
    <Card className="gap-3 p-4.5">
      <div className="flex items-start gap-3.5">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {source.toolName && (
              <span className="rounded-md bg-primary/10 px-2 py-0.5 font-mono text-[10.5px] text-primary">
                {source.toolName}
              </span>
            )}
            {source.kind && (
              <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 font-mono text-[10.5px] text-muted-foreground">
                {source.kind === 'youtube' ? (
                  <Clapperboard className="size-3" />
                ) : (
                  <FileText className="size-3" />
                )}
                {source.kind === 'youtube' ? 'video' : 'documentación'}
              </span>
            )}
            {source.relevanceScore !== undefined && (
              <span className="rounded-md bg-secondary px-2 py-0.5 font-mono text-[10.5px] text-muted-foreground">
                {source.relevanceScore}% match
              </span>
            )}
          </div>
          <h3 className="mb-2 font-display text-[15.5px] font-medium leading-snug text-ink">
            {source.title}
          </h3>
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="rounded-md bg-secondary px-2 py-0.5 font-mono text-[10.5px] text-muted-foreground">
              {source.plat}
            </span>
            {source.verified ? (
              <Badge variant="success">
                <ShieldCheck className="size-3" /> Verificada
              </Badge>
            ) : (
              <Badge variant="destructive">
                <AlertTriangle className="size-3" /> Requiere revisión
              </Badge>
            )}
            {source.suggestedUse && (
              <span className="rounded-md bg-accent px-2 py-0.5 font-mono text-[10.5px] text-primary">
                uso: {source.suggestedUse}
              </span>
            )}
          </div>
        </div>
        {!approved && (
          <Button variant="outline-destructive" size="sm" onClick={onDiscard}>
            Descartar
          </Button>
        )}
      </div>
      <blockquote className="border-l-[3px] border-accent pl-3.5 text-[13.5px] italic leading-relaxed">
        {source.quote}
      </blockquote>
      {source.verificationReason && (
        <div
          className={cn(
            'flex items-start gap-2 rounded-lg px-3 py-2.5 text-[12.5px] leading-relaxed',
            requiresReview ? 'bg-destructive/8' : 'bg-success/10',
          )}
        >
          {requiresReview ? (
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-destructive" />
          ) : (
            <ShieldCheck className="mt-0.5 size-3.5 shrink-0 text-success" />
          )}
          <span>{source.verificationReason}</span>
        </div>
      )}
      {source.url && (
        <Button asChild variant="ghost" size="sm" className="w-fit px-0">
          <a href={source.url} target="_blank" rel="noreferrer">
            {requiresReview && source.kind === 'youtube' ? 'Abrir canal candidato' : 'Abrir fuente concreta'}
            <ExternalLink className="size-3.5" />
          </a>
        </Button>
      )}
      {source.videoPreview && (
        <SourceVideoPreview
          preview={source.videoPreview}
          open={videoOpen}
          onOpenChange={setVideoOpen}
        />
      )}
    </Card>
  )
}

/* ── Corpus de fuentes (encima de Módulos) ─────────────────────── */
function CorpusSection({ route }: { route: LearningRoute }) {
  const { isCorpusApproved, approveCorpus, discardedSources, discardSource } = useStore()
  const approved = isCorpusApproved(route.id)
  const discarded = discardedSources(route.id)
  const sources = route.sources.filter((_, i) => !discarded.includes(i))
  const verified = sources.filter((s) => s.verified).length
  const groupedSources = sources.reduce<Record<string, { source: Source; index: number }[]>>((groups, source) => {
    const key = source.toolName || 'Fuentes generales'
    groups[key] = [...(groups[key] ?? []), { source, index: route.sources.indexOf(source) }]
    return groups
  }, {})
  const detectedTools = Object.keys(groupedSources)

  return (
    <section className="mb-8">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <h2 className="font-display text-xl font-medium text-ink">Revisión de fuentes</h2>
          {approved && (
            <Badge variant="success">
              <Check className="size-3" /> aprobado
            </Badge>
          )}
        </div>
        <span className="font-mono text-[11px] text-muted-foreground">
          {sources.length} candidatas · {verified} verificadas
        </span>
      </div>

      {!approved && (
        <div className="mb-4 flex items-start gap-3 rounded-xl bg-secondary px-4.5 py-3.5">
          <Search className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <p className="text-[13px] leading-relaxed">
            Aprueba las fuentes antes de que aterricen en el contenido. El agente prioriza canales
            y dominios verificados por herramienta/vendor; deja en revisión lo que no pase la
            política.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {detectedTools.map((tool) => (
          <div key={tool} className="rounded-xl border-[1.5px] border-secondary p-3">
            <div className="mb-3 flex items-center justify-between gap-3 px-1">
              <div>
                <h3 className="font-display text-[15px] font-medium text-ink">{tool}</h3>
                <p className="mt-0.5 font-mono text-[10.5px] text-muted-foreground">
                  {groupedSources[tool]?.length ?? 0} fuentes candidatas
                </p>
              </div>
              <Badge variant="outline">
                {groupedSources[tool]?.filter((item) => item.source.verified).length ?? 0} verificadas
              </Badge>
            </div>
            <div className="flex flex-col gap-3">
              {groupedSources[tool]?.map(({ source, index }) => (
                <SourceCard
                  key={`${source.title}-${index}`}
                  source={source}
                  approved={approved}
                  onDiscard={() => {
                    discardSource(route.id, index)
                    toast.info('Fuente descartada', { description: source.title })
                  }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {!approved && (
        <div className="mt-4 flex justify-end">
          <Button
            onClick={() => {
              approveCorpus(route.id)
              toast.success('Fuentes aprobadas', {
                description: `${verified} fuentes verificadas alimentan la base de conocimiento.`,
              })
            }}
          >
            Aprobar fuentes <ArrowRight />
          </Button>
        </div>
      )}
    </section>
  )
}

/* ── Panel de asset (tab visible) ──────────────────────────────── */
function ContentReviewPanel({
  route,
  module,
  content,
}: {
  route: LearningRoute
  module: RouteModule
  content: ModuleContentRef
}) {
  const router = useRouter()
  const {
    contentStatusOf,
    approveContent,
    refineContent,
    isStoryboardApproved,
    isLabGuideApproved,
    storyboardVideoUrlOf,
  } = useStore()



  const status = contentStatusOf(route.id, module.id, content.kind, content.status)
  const label = KIND_LABEL[content.kind]
  const isVideo = content.kind === 'video'
  const isLab = content.kind === 'lab'
  const storyboardOk = isStoryboardApproved(route.id)
  const labGuideOk = isLabGuideApproved(route.id)
  const videoNeedsReview = isVideo && status !== 'aprobado' && !storyboardOk
  const labNeedsReview = isLab && status !== 'aprobado' && !labGuideOk
  const showVideoPreview = !isVideo || storyboardOk || status === 'aprobado'
  const storyboardVideoUrl = isVideo ? storyboardVideoUrlOf(route.id) : ''

  const approveButton = (
    <Button
      variant={status === 'aprobado' ? 'outline' : 'success'}
      size="sm"
      disabled={status === 'aprobado'}
      onClick={() => {
        approveContent(route.id, module.id, content.kind)
        toast.success(`${label} aprobado`, { description: `${module.name} · ${route.name}` })
      }}
    >
      {status === 'aprobado' ? (
        <>
          <CircleCheck /> Aprobado
        </>
      ) : (
        <>
          <Check /> Aprobar
        </>
      )}
    </Button>
  )

  return (
    <div className="rounded-xl border-[1.5px] border-secondary bg-background/70 p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="font-display text-lg font-medium text-ink">{label}</span>
            <StatusBadge status={status} />
          </div>
          <p className="max-w-2xl text-[13px] leading-relaxed text-muted-foreground">
            {content.summary}
          </p>
        </div>
        <div className="flex gap-2.5">
          {approveButton}
          <RefinePopover
            label={label}
            onRefine={() => refineContent(route.id, module.id, content.kind)}
          >
            <Button variant="outline-primary" size="sm">
              <Sparkles /> Refinar
            </Button>
          </RefinePopover>
        </div>
      </div>

      {videoNeedsReview && (
        <button
          type="button"
          onClick={() => router.push(`/ruta/${route.id}/video-storyboard`)}
          className="mb-4 flex w-full cursor-pointer items-center gap-3 rounded-lg border-[1.5px] border-accent bg-primary/8 px-3.5 py-3 text-left transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
        >
          <Clapperboard className="size-4.5 text-primary" />
          <span className="flex-1">
            <span className="block text-[13px] font-semibold text-ink">
              Revisar guion y storyboard
            </span>
            <span className="mt-0.5 block text-[11.5px] text-muted-foreground">
              Recomendado para validar el guion. También puedes aprobar el video directamente.
            </span>
          </span>
          <ArrowRight className="size-4 text-primary" />
        </button>
      )}

      {isVideo && storyboardOk && status !== 'aprobado' && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-success/10 px-3.5 py-2.5 text-[12.5px] text-foreground">
          <CircleCheck className="size-4 text-success" />
          Guion y storyboard aprobados — el video está listo para tu aprobación.
        </div>
      )}

      {labNeedsReview && (
        <button
          type="button"
          onClick={() => router.push(`/ruta/${route.id}/lab-guia`)}
          className="mb-4 flex w-full cursor-pointer items-center gap-3 rounded-lg border-[1.5px] border-accent bg-primary/8 px-3.5 py-3 text-left transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
        >
          <FlaskConical className="size-4.5 text-primary" />
          <span className="flex-1">
            <span className="block text-[13px] font-semibold text-ink">
              Personalizar guía del laboratorio
            </span>
            <span className="mt-0.5 block text-[11.5px] text-muted-foreground">
              Recomendado para ajustar la práctica. También puedes aprobar el laboratorio directamente.
            </span>
          </span>
          <ArrowRight className="size-4 text-primary" />
        </button>
      )}

      {isLab && labGuideOk && status !== 'aprobado' && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-success/10 px-3.5 py-2.5 text-[12.5px] text-foreground">
          <CircleCheck className="size-4 text-success" />
          Guía del laboratorio aprobada — el laboratorio está listo para tu aprobación.
        </div>
      )}

      {/* Preview real del contenido */}
      <div className="mb-4">
        {isVideo && !showVideoPreview ? (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-secondary bg-secondary/40 px-6 py-10 text-center">
            <div className="flex size-14 items-center justify-center rounded-full bg-background text-primary shadow-sm">
              <Play className="size-5" />
            </div>
            <div className="max-w-sm">
              <p className="font-display text-[15px] font-medium text-ink">
                Vista previa vacía
              </p>
              <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                El video se muestra después de generar o aprobar el storyboard. Por ahora, esta
                tarjeta queda en blanco para no mezclar placeholder con material real.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/ruta/${route.id}/video-storyboard`)}
            >
              Ir a storyboard
            </Button>
          </div>
        ) : (
          <ContentPreview kind={content.kind} pack={route.pack} videoUrl={storyboardVideoUrl} />
        )}
      </div>

    </div>
  )
}

/* ── Página ────────────────────────────────────────────────────── */
export default function Ruta() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const {
    routes,
    isCorpusApproved,
    markGenerated,
    contentStatusOf,
    moduleStatusOf,
    approveModule,
    routeProgressOf,
  } = useStore()
  const route = useMemo(() => routes.find((r) => r.id === id), [routes, id])
  const [selectedModuleIndex, setSelectedModuleIndex] = useState(0)
  const [selectedContentKind, setSelectedContentKind] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  const progress = useMemo(
    () => (route ? routeProgressOf(route) : { done: 0, total: 0, pct: 0 }),
    [route, routeProgressOf],
  )

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

  const corpusOk = isCorpusApproved(route.id)
  const selectedModule = route.modules[selectedModuleIndex] ?? route.modules[0]
  const selectedModuleStatus = selectedModule ? moduleStatusOf(route.id, selectedModule) : 'borrador'
  const selectedModuleContents = selectedModule?.contents ?? []
  const selectedContent =
    selectedModuleContents.find((content) => content.kind === selectedContentKind) ?? selectedModuleContents[0]
  const selectedTab = selectedContent?.kind ?? ''
  const approvedAssets = selectedModule
    ? selectedModuleContents.filter(
        (content) => contentStatusOf(route.id, selectedModule.id, content.kind, content.status) === 'aprobado',
      ).length
    : 0
  const allAssetsApproved =
    selectedModuleContents.length > 0 && approvedAssets === selectedModuleContents.length
  const isFirstModule = selectedModuleIndex === 0
  const isLastModule = selectedModuleIndex >= route.modules.length - 1

  const goToModule = (nextIndex: number) => {
    const boundedIndex = Math.min(Math.max(nextIndex, 0), route.modules.length - 1)
    const nextModule = route.modules[boundedIndex]
    setSelectedModuleIndex(boundedIndex)
    setSelectedContentKind(nextModule?.contents[0]?.kind ?? null)
  }

  const generate = () => {
    setGenerating(true)
    toast.loading('Generando el material de todos los módulos…', { id: 'gen' })
    window.setTimeout(() => {
      markGenerated(route.id)
      toast.success('Contenido generado', {
        id: 'gen',
        description: 'Revisa el asset final antes de publicar.',
      })
      router.push(`/ruta/${route.id}/asset-final`)
    }, 1400)
  }

  const generateButton = (
    <Button disabled={!corpusOk || generating} onClick={generate}>
      {generating ? (
        <>
          <Loader2 className="animate-spin" /> Generando…
        </>
      ) : (
        <>
          <Wand2 /> Generar contenido
        </>
      )}
    </Button>
  )

  return (
    <div className="mx-auto grid max-w-[1120px] items-start gap-9 lg:grid-cols-[1fr_300px]">
      <div>
        <Eyebrow>
          Ruta {route.id} · {route.name}
        </Eyebrow>
        <PageTitle className="mb-5 text-[31px]">{route.name}</PageTitle>

        {/* Objetivo */}
        <Card className="mb-7 gap-2 border-l-[3px] border-l-primary p-5">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-primary">
            TL;DR · Objetivo de la ruta
          </div>
          <p className="text-[14.5px] leading-relaxed">{route.objective}</p>
        </Card>

        {/* Corpus encima de Módulos */}
        <CorpusSection route={route} />

        {/* Módulo activo */}
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="font-display text-xl font-medium text-ink">Módulos</h2>
          <span className="font-mono text-[11px] text-muted-foreground">
            {progress.done} de {route.modules.length} aprobados
          </span>
        </div>

        {selectedModule && (
          <Card className={cn('gap-5 p-5', selectedModuleStatus === 'en-revision' && 'border-primary')}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3.5">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 font-mono text-[13px] font-semibold text-primary">
                  {selectedModule.num}
                </span>
                <span className="min-w-0">
                  <span className="block font-display text-xl font-medium leading-tight text-ink">
                    {selectedModule.name}
                  </span>
                  <span className="mt-1 block font-mono text-[10px] uppercase tracking-[0.05em] text-muted-foreground">
                    {selectedModule.type} · módulo {selectedModuleIndex + 1} de {route.modules.length}
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={selectedModuleStatus} />
                <Badge variant={allAssetsApproved ? 'success' : 'muted'}>
                  {approvedAssets}/{selectedModuleContents.length} assets
                </Badge>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-secondary px-3.5 py-3">
              <Button
                variant="outline"
                size="sm"
                disabled={isFirstModule}
                onClick={() => goToModule(selectedModuleIndex - 1)}
              >
                <ArrowLeft /> Módulo anterior
              </Button>
              <div className="flex flex-wrap justify-center gap-1.5">
                {route.modules.map((module, index) => {
                  const status = moduleStatusOf(route.id, module)
                  return (
                    <button
                      type="button"
                      key={module.id}
                      onClick={() => goToModule(index)}
                      className={cn(
                        'size-8 rounded-lg border-[1.5px] font-mono text-[11px] font-semibold transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30',
                        index === selectedModuleIndex
                          ? 'border-primary bg-primary text-primary-foreground'
                          : status === 'aprobado'
                            ? 'border-success bg-success/10 text-success'
                            : 'border-input bg-card text-muted-foreground hover:border-primary',
                      )}
                      aria-label={`Ver módulo ${module.num}`}
                    >
                      {status === 'aprobado' ? <Check className="mx-auto size-3.5" /> : module.num}
                    </button>
                  )
                })}
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={isLastModule}
                onClick={() => goToModule(selectedModuleIndex + 1)}
              >
                Siguiente módulo <ArrowRight />
              </Button>
            </div>

            {selectedModuleContents.length > 0 ? (
              <Tabs value={selectedTab} onValueChange={setSelectedContentKind}>
                <TabsList className="w-full overflow-x-auto border-b-[1.5px]">
                  {selectedModuleContents.map((content) => {
                    const status = contentStatusOf(route.id, selectedModule.id, content.kind, content.status)
                    return (
                      <TabsTrigger key={content.kind} value={content.kind} className="px-3">
                        {status === 'aprobado' && <CircleCheck className="size-3.5 text-success" />}
                        {KIND_LABEL[content.kind]}
                      </TabsTrigger>
                    )
                  })}
                </TabsList>

                {selectedModuleContents.map((content) => (
                  <TabsContent key={content.kind} value={content.kind} className="mt-3">
                    <ContentReviewPanel route={route} module={selectedModule} content={content} />
                  </TabsContent>
                ))}
              </Tabs>
            ) : (
              <div className="rounded-xl border-[1.5px] border-dashed border-input p-6 text-center text-[13px] text-muted-foreground">
                Este módulo todavía no tiene assets generados.
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-secondary px-3.5 py-3">
              <span className="text-[12.5px] leading-relaxed text-muted-foreground">
                {allAssetsApproved
                  ? 'Todos los assets de este módulo están aprobados.'
                  : 'Revisa y aprueba cada asset antes de cerrar este módulo.'}
              </span>
              {allAssetsApproved ? (
                <Button
                  variant={isLastModule ? 'success' : 'outline-primary'}
                  size="sm"
                  onClick={() => {
                    approveModule(route.id, selectedModule)
                    toast.success('Módulo aprobado', { description: `${selectedModule.name} · ${route.name}` })
                    if (!isLastModule) goToModule(selectedModuleIndex + 1)
                  }}
                >
                  {isLastModule ? (
                    <>
                      <CircleCheck /> Módulo aprobado
                    </>
                  ) : (
                    <>
                      Continuar al siguiente módulo <ArrowRight />
                    </>
                  )}
                </Button>
              ) : (
                <Badge variant="outline">
                  {approvedAssets} de {selectedModuleContents.length} aprobados
                </Badge>
              )}
            </div>
          </Card>
        )}

        {/* Generar contenido */}
        <Separator className="mt-6 mb-5" />
        <div className="flex items-center justify-between gap-4">
          <span className="text-[12.5px] leading-relaxed text-muted-foreground">
            {corpusOk ? (
              <>
                Genera el material de <b className="text-ink">todos los módulos</b> de la ruta en
                una sola pasada.
              </>
            ) : (
              <>
                <b className="text-ink">Aprueba las fuentes</b> para habilitar la generación de
                contenido.
              </>
            )}
          </span>
          {corpusOk ? (
            generateButton
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <span>{generateButton}</span>
              </TooltipTrigger>
              <TooltipContent>Primero aprueba las fuentes</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      {/* Provenance */}
      <Card className="sticky top-20 gap-4 p-5">
        <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          Provenance · Ruta
        </div>
        <div>
          <div className="mb-1 text-[11px] text-muted-foreground">Modelo de generación</div>
          <div className="font-mono text-[13.5px] text-ink">Gemini 2.5 · Veo 3</div>
        </div>
        <Separator className="bg-secondary" />
        <div className="flex items-center gap-2">
          <span className="size-2 rounded-full bg-success" />
          <span className="text-[13px]">
            <b className="text-ink">{route.sources.filter((s) => s.verified).length}</b> fuentes
            verificadas
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="size-2 rounded-full bg-destructive" />
          <span className="text-[13px]">
            <b className="text-ink">{route.sources.filter((s) => !s.verified).length}</b> sin
            verificar
          </span>
        </div>
        <Separator className="bg-secondary" />
        <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
          <Info className="size-3.5" />
          Cada asset registra modelo y fuentes usadas.
        </div>
      </Card>
    </div>
  )
}
