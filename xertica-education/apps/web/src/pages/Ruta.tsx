import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Clapperboard,
  FlaskConical,
  Info,
  Loader2,
  ShieldCheck,
  Sparkles,
  Wand2,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Eyebrow, PageTitle } from '@/components/PageHeader'
import { StatusBadge } from '@/components/content/StatusBadge'
import { ContentPreview } from '@/components/content/ContentPreview'
import { SourceVideoPreview } from '@/components/content/SourceVideoPreview'
import { RefinePopover } from '@/components/RefinePopover'
import { getRoute } from '@/data/routes'
import {
  KIND_LABEL,
  type LearningRoute,
  type ModuleContentRef,
  type RouteModule,
  type Source,
} from '@/lib/types'
import { useStore } from '@/store'
import { cn } from '@/lib/utils'

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

  return (
    <Card className="gap-3 p-4.5">
      <div className="flex items-start gap-3.5">
        <div className="min-w-0 flex-1">
          <h3 className="mb-2 font-display text-[15.5px] font-medium leading-snug text-ink">
            {source.title}
          </h3>
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="rounded-md bg-secondary px-2 py-0.5 font-mono text-[10.5px] text-muted-foreground">
              {source.plat}
            </span>
            {source.verified ? (
              <Badge variant="success">
                <ShieldCheck className="size-3" /> Verificada Google
              </Badge>
            ) : (
              <Badge variant="destructive">
                <AlertTriangle className="size-3" /> Sin verificar
              </Badge>
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

  return (
    <section className="mb-8">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <h2 className="font-display text-xl font-medium text-ink">Revisar corpus de fuentes</h2>
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
          <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <p className="text-[13px] leading-relaxed">
            Aprueba las fuentes antes de que aterricen en el contenido. Solo se admiten fuentes
            verificables de Google. Descarta cualquier fuente sin verificar antes de continuar.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {route.sources.map((f, i) => {
          if (discarded.includes(i)) return null
          return (
            <SourceCard
              key={f.title}
              source={f}
              approved={approved}
              onDiscard={() => {
                discardSource(route.id, i)
                toast.info('Fuente descartada', { description: f.title })
              }}
            />
          )
        })}
      </div>

      {!approved && (
        <div className="mt-4 flex justify-end">
          <Button
            onClick={() => {
              approveCorpus(route.id)
              toast.success('Corpus aprobado', {
                description: `${verified} fuentes verificadas alimentan la base de conocimiento.`,
              })
            }}
          >
            Aprobar corpus <ArrowRight />
          </Button>
        </div>
      )}
    </section>
  )
}

/* ── Fila de contenido (colapsable + aprobar/refinar) ──────────── */
function ContentRow({
  route,
  module,
  content,
}: {
  route: LearningRoute
  module: RouteModule
  content: ModuleContentRef
}) {
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  const { contentStatusOf, approveContent, refineContent, isStoryboardApproved, isLabGuideApproved } = useStore()

  const status = contentStatusOf(route.id, module.id, content.kind, content.status)
  const label = KIND_LABEL[content.kind]
  const isVideo = content.kind === 'video'
  const isLab = content.kind === 'lab'
  const storyboardOk = isStoryboardApproved(route.id)
  const labGuideOk = isLabGuideApproved(route.id)
  const videoBlocked = isVideo && status !== 'aprobado' && !storyboardOk
  const labBlocked = isLab && status !== 'aprobado' && !labGuideOk

  const approveButton = (
    <Button
      variant={status === 'aprobado' ? 'outline' : 'success'}
      size="sm"
      disabled={status === 'aprobado' || videoBlocked || labBlocked}
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
    <div className="mb-2 rounded-lg border-[1.5px] border-secondary">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center gap-3 rounded-lg px-3.5 py-2.75 text-left outline-none transition-colors hover:bg-background/70 focus-visible:ring-[3px] focus-visible:ring-ring/30"
      >
        {open ? (
          <ChevronDown className="size-3.5 text-input" />
        ) : (
          <ChevronRight className="size-3.5 text-input" />
        )}
        <span className="flex-1 text-[13.5px]">{label}</span>
        <StatusBadge status={status} />
      </button>

      {open && (
        <div className="border-t border-secondary px-4 pt-3.5 pb-4 pl-9.5">
          <p className="mb-4 text-[13px] leading-relaxed text-muted-foreground">
            {content.summary}
          </p>

          {videoBlocked && (
            <button
              type="button"
              onClick={() => nav(`/ruta/${route.id}/video-storyboard`)}
              className="mb-4 flex w-full cursor-pointer items-center gap-3 rounded-lg border-[1.5px] border-accent bg-primary/8 px-3.5 py-3 text-left transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
            >
              <Clapperboard className="size-4.5 text-primary" />
              <span className="flex-1">
                <span className="block text-[13px] font-semibold text-ink">
                  Revisar guion y storyboard
                </span>
                <span className="mt-0.5 block text-[11.5px] text-muted-foreground">
                  El video requiere aprobar guion y storyboard antes de generarse.
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

          {labBlocked && (
            <button
              type="button"
              onClick={() => nav(`/ruta/${route.id}/lab-guia`)}
              className="mb-4 flex w-full cursor-pointer items-center gap-3 rounded-lg border-[1.5px] border-accent bg-primary/8 px-3.5 py-3 text-left transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
            >
              <FlaskConical className="size-4.5 text-primary" />
              <span className="flex-1">
                <span className="block text-[13px] font-semibold text-ink">
                  Personalizar guía del laboratorio
                </span>
                <span className="mt-0.5 block text-[11.5px] text-muted-foreground">
                  El laboratorio requiere aprobar la guía paso a paso antes de generarse.
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
            <ContentPreview kind={content.kind} pack={route.pack} />
          </div>

          <div className="flex gap-2.5">
            {videoBlocked || labBlocked ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>{approveButton}</span>
                </TooltipTrigger>
                <TooltipContent>
                  {videoBlocked
                    ? 'Primero aprueba el guion y storyboard'
                    : 'Primero aprueba la guía del laboratorio'}
                </TooltipContent>
              </Tooltip>
            ) : (
              approveButton
            )}
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
      )}
    </div>
  )
}

/* ── Página ────────────────────────────────────────────────────── */
export default function Ruta() {
  const { id } = useParams()
  const nav = useNavigate()
  const { routes, isCorpusApproved, markGenerated, contentStatusOf } = useStore()
  const route = useMemo(() => routes.find((r) => r.id === id), [routes, id])
  const [openModule, setOpenModule] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  const approvedModules = useMemo(() => {
    if (!route) return 0
    return route.modules.filter((m) =>
      m.contents.every(
        (c) => contentStatusOf(route.id, m.id, c.kind, c.status) === 'aprobado',
      ),
    ).length
  }, [route, contentStatusOf])

  if (!route) {
    return (
      <div className="mx-auto max-w-md pt-16 text-center">
        <PageTitle>Ruta no encontrada</PageTitle>
        <Button asChild className="mt-6">
          <Link to="/">Volver a las rutas</Link>
        </Button>
      </div>
    )
  }

  const corpusOk = isCorpusApproved(route.id)
  const activeModule = route.modules.find((m) => m.status === 'en-revision')
  const effectiveOpen = openModule ?? activeModule?.id ?? route.modules[0]?.id ?? null

  const generate = () => {
    setGenerating(true)
    toast.loading('Generando el material de todos los módulos…', { id: 'gen' })
    window.setTimeout(() => {
      markGenerated(route.id)
      toast.success('Contenido generado', {
        id: 'gen',
        description: 'Revisa el asset final antes de publicar.',
      })
      nav(`/ruta/${route.id}/asset-final`)
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

        {/* Módulos */}
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="font-display text-xl font-medium text-ink">Módulos</h2>
          <span className="font-mono text-[11px] text-muted-foreground">
            {approvedModules} de {route.modules.length} aprobados
          </span>
        </div>

        <div className="flex flex-col gap-3">
          {route.modules.map((m) => {
            const isOpen = effectiveOpen === m.id
            return (
              <Card
                key={m.id}
                className={cn('gap-0 overflow-hidden p-0', m.status === 'en-revision' && 'border-primary')}
              >
                <button
                  type="button"
                  onClick={() => setOpenModule(isOpen ? '' : m.id)}
                  className="flex w-full cursor-pointer items-center gap-3.5 px-4.5 py-4 text-left outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30"
                >
                  {isOpen ? (
                    <ChevronDown className="size-3.5 text-input" />
                  ) : (
                    <ChevronRight className="size-3.5 text-input" />
                  )}
                  <span className="font-mono text-[13px] font-semibold text-primary">{m.num}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-display text-base text-ink">{m.name}</span>
                    <span className="mt-0.5 block font-mono text-[10px] uppercase tracking-[0.05em] text-muted-foreground">
                      {m.type}
                    </span>
                  </span>
                  <StatusBadge status={m.status} />
                </button>
                {isOpen && (
                  <div className="border-t-[1.5px] border-secondary px-4.5 pt-3 pb-4 pl-11">
                    {m.contents.map((c) => (
                      <ContentRow key={c.kind} route={route} module={m} content={c} />
                    ))}
                  </div>
                )}
              </Card>
            )
          })}
        </div>

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
                <b className="text-ink">Aprueba el corpus</b> para habilitar la generación de
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
              <TooltipContent>Primero aprueba el corpus de fuentes</TooltipContent>
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
