'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { ArrowRight, BookMarked, Check, GripVertical, Plus, SquarePen, Sparkles, X } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Card } from '@/shared/ui/card'
import { Input } from '@/shared/ui/input'
import { Textarea } from '@/shared/ui/textarea'
import { Separator } from '@/shared/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'
import { Eyebrow, PageDescription, PageTitle } from '@/shared/components/PageHeader'
import { CONTENT_KINDS, KIND_LABEL, type ProposalModule } from '@/shared/lib/types'
import { useStore, mapRouteModulesToProposal, mapProposalToRouteModules } from '@/shared/store'
import { cn } from '@/shared/lib/utils'
import { api } from '@/shared/lib/api'

function ModuleRow({ m, index }: { m: ProposalModule; index: number }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: m.id,
  })
  const { refineProposal, editProposal, removeProposal, toggleProposalComp, proposal } = useStore()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(m.title)
  const [desc, setDesc] = useState(m.desc)

  const startEdit = () => {
    setTitle(m.title)
    setDesc(m.desc)
    setEditing(true)
  }

  const save = () => {
    const nextTitle = title.trim()
    const nextDesc = desc.trim()
    if (!nextTitle || !nextDesc) return
    editProposal(m.id, nextTitle, nextDesc)
    setEditing(false)
  }

  const cancel = () => setEditing(false)

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        'rounded-xl border-[1.5px] bg-card p-4',
        isDragging && 'z-10 border-primary opacity-70 shadow-(--shadow-lift)',
        editing && 'border-primary',
      )}
    >
      <div className="mb-1.5 flex items-center gap-2.5">
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              {...attributes}
              {...listeners}
              disabled={editing}
              className="cursor-grab touch-none rounded p-1 text-input outline-none hover:text-muted-foreground focus-visible:ring-[3px] focus-visible:ring-ring/30 active:cursor-grabbing disabled:cursor-not-allowed disabled:opacity-40"
            >
              <GripVertical className="size-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent>Arrastra para reordenar</TooltipContent>
        </Tooltip>

        <span className="font-mono text-xs font-semibold text-primary">
          {String(index + 1).padStart(2, '0')}
        </span>
        {editing ? (
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="h-8 flex-1 font-display text-[14.5px]"
            placeholder="Título del módulo"
            autoFocus
          />
        ) : (
          <span className="flex-1 font-display text-[15.5px] text-ink">{m.title}</span>
        )}
        <Badge variant="default" className="normal-case tracking-normal">
          {m.min} min
        </Badge>
        {!editing && (
          <>
            <Button
              variant="outline-primary"
              size="sm"
              className="h-7 px-2.5 font-mono text-[11px]"
              onClick={startEdit}
            >
              <SquarePen className="size-3" /> Editar
            </Button>
            <Button variant="outline-primary" size="sm" className="h-7 px-2.5 font-mono text-[11px]" onClick={() => refineProposal(m.id)}>
              <Sparkles className="size-3" /> IA
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 text-input hover:text-destructive"
              disabled={proposal.length <= 1}
              onClick={() => removeProposal(m.id)}
            >
              <X className="size-3.5" />
            </Button>
          </>
        )}
      </div>

      {editing ? (
        <div className="pl-[52px]">
          <Textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            className="mb-3 text-[13px]"
            rows={2}
            placeholder="Describe el objetivo de este módulo"
          />
          <div className="mb-3 flex gap-2">
            <Button size="sm" onClick={save}>
              <Check className="size-3.5" /> Guardar
            </Button>
            <Button variant="outline" size="sm" onClick={cancel}>
              Cancelar
            </Button>
          </div>
        </div>
      ) : (
        <p className="mb-3 pl-[52px] text-[13px] leading-relaxed text-muted-foreground">{m.desc}</p>
      )}

      <div className="flex flex-wrap gap-2 pl-[52px]">
        {CONTENT_KINDS.map((kind) => {
          const on = m.comps[kind]
          return (
            <button
              key={kind}
              type="button"
              disabled={editing}
              onClick={() => toggleProposalComp(m.id, kind)}
              className={cn(
                'inline-flex cursor-pointer items-center gap-1 rounded-full border-[1.5px] px-2.75 py-1.25 text-xs transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50',
                on
                  ? 'border-primary bg-primary text-white'
                  : 'border-input bg-card text-muted-foreground hover:border-primary/50',
              )}
            >
              {on && <Check className="size-3" strokeWidth={3} />}
              {KIND_LABEL[kind]}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ModuleSkeleton() {
  return (
    <div className="rounded-xl border-[1.5px] bg-card p-4 animate-pulse">
      <div className="mb-3 flex items-center gap-2.5">
        <div className="h-4 w-4 rounded bg-secondary" />
        <div className="h-4 w-8 rounded bg-secondary" />
        <div className="h-4 flex-1 rounded bg-secondary" />
        <div className="h-5 w-16 rounded bg-secondary" />
      </div>
      <div className="pl-[52px]">
        <div className="mb-2 h-3 w-3/4 rounded bg-secondary" />
        <div className="mb-4 h-3 w-1/2 rounded bg-secondary" />
        <div className="flex gap-2">
          <div className="h-6 w-16 rounded-full bg-secondary" />
          <div className="h-6 w-20 rounded-full bg-secondary" />
          <div className="h-6 w-24 rounded-full bg-secondary" />
        </div>
      </div>
    </div>
  )
}

function FailureState({ onRegenerate }: { onRegenerate: () => void }) {
  return (
    <Card className="p-6 text-center border-destructive bg-destructive/5 flex flex-col items-center gap-4">
      <div className="size-12 rounded-full bg-destructive/10 flex items-center justify-center text-destructive">
        <X className="size-6" />
      </div>
      <div>
        <h3 className="font-display text-base font-semibold text-ink">La generación falló</h3>
        <p className="text-[13px] text-muted-foreground mt-1 max-w-[400px]">
          Hubo un problema de conexión o el formato del LLM no pudo ser interpretado. 
          Puedes reintentar la propuesta curricular con el mismo brief.
        </p>
      </div>
      <Button onClick={onRegenerate} className="gap-2">
        <Sparkles className="size-4" /> Regenerar estructura
      </Button>
    </Card>
  )
}

export default function EstructuraPropuesta() {
  const router = useRouter()
  const {
    proposal,
    reorderProposal,
    addProposal,
    activeRouteId,
    fetchRoutes,
    routes,
    activeJobs,
    trackJob,
    structureJobId,
    setStructureJobId,
    setProposal,
    proposalLoadedRouteId,
    setProposalLoadedRouteId,
    pendingDeepResearch,
    setPendingDeepResearch,
    replaceRouteSources,
  } = useStore()
  const [approving, setApproving] = useState(false)

  const activeRoute = routes.find((r) => r.id === activeRouteId)
  const currentJob = structureJobId ? activeJobs[structureJobId] : null
  const isLoading = !!structureJobId && (!currentJob || currentJob.status === 'queued' || currentJob.status === 'running')
  const isFailed = currentJob?.status === 'failed'

  useEffect(() => {
    if (!activeRouteId) return
    const activeRoute = routes.find((r) => r.id === activeRouteId)
    if (activeRoute && Array.isArray(activeRoute.modules) && activeRoute.modules.length > 0) {
      if (proposalLoadedRouteId !== activeRouteId && !structureJobId) {
        setProposal(mapRouteModulesToProposal(activeRoute.modules))
        setProposalLoadedRouteId(activeRouteId)
      }
    }
  }, [activeRouteId, routes, proposalLoadedRouteId, structureJobId, setProposal, setProposalLoadedRouteId])

  useEffect(() => {
    if (!structureJobId) return
    let active = true

    trackJob(structureJobId)
      .then(async (job) => {
        if (!active) return
        if (job.status === 'completed') {
          await fetchRoutes()
          setProposalLoadedRouteId(null) // trigger reload

          if (pendingDeepResearch && activeRouteId) {
            try {
              const toastId = toast.loading('Investigando fuentes verificadas...', {
                description: 'Detectando herramientas, canales oficiales y documentación relevante.',
              })
              
              // We need the brief and customer context to run deep research
              const refreshedRoutes = await api.request<any[]>('/learning-paths/')
              const activeRouteObj = refreshedRoutes.find((r) => r.id === activeRouteId)
              const brief = activeRouteObj?.objective || ''
              const customerContext = activeRouteObj?.customerContext || {}

              const research = await api.request<any>(
                `/learning-paths/${activeRouteId}/deep-research`,
                {
                  method: 'POST',
                  body: JSON.stringify({ brief, customerContext }),
                },
              )
              replaceRouteSources(activeRouteId, research.sources)
              setPendingDeepResearch(false)
              const toolNames = research.detected_tools.map((t: any) => t.tool).join(', ')
              toast.success('Deep Research listo para enriquecer los assets', {
                id: toastId,
                description: `${research.sources.length} recomendaciones para ${toolNames || 'la ruta'}.`,
              })
            } catch (err) {
              console.error('Deep research failed:', err)
              toast.error('Error en deep research')
            }
          }

          setStructureJobId(null)
        }
      })
      .catch((err) => {
        console.error('Job tracking failed:', err)
      })

    return () => {
      active = false
    }
  }, [structureJobId, trackJob, fetchRoutes, activeRouteId, pendingDeepResearch, replaceRouteSources, setPendingDeepResearch, setStructureJobId, setProposalLoadedRouteId])

  const regenerate = async () => {
    if (!activeRouteId) return
    const toastId = toast.loading('Regenerando estructura con IA...')
    try {
      const activeRouteObj = routes.find(r => r.id === activeRouteId)
      const brief = activeRouteObj?.objective || ''
      const customerContext = activeRouteObj?.customerContext || {}

      const genResult = await api.request<{ job_id: string }>(
        `/learning-paths/${activeRouteId}/generate-structure`,
        {
          method: 'POST',
          body: JSON.stringify({ brief, customerContext }),
        }
      )
      setStructureJobId(genResult.job_id)
      toast.success('Nueva generación iniciada', { id: toastId })
    } catch (err) {
      console.error(err)
      toast.error('Error al iniciar regeneración', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    }
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (over && active.id !== over.id) {
      reorderProposal(String(active.id), String(over.id))
    }
  }

  const approve = async () => {
    setApproving(true)
    const targetId = activeRouteId || '01'
    const toastId = toast.loading('Guardando y aprobando estructura...')
    try {
      // Guardar cambios en el backend antes de aprobar
      const backendModules = mapProposalToRouteModules(proposal)
      await api.request(`/learning-paths/${targetId}`, {
        method: 'PATCH',
        body: JSON.stringify({ modules: backendModules })
      })

      await api.request(`/learning-paths/${targetId}/approve`, { method: 'POST' })
      await fetchRoutes()
      toast.success('Estructura aprobada', {
        id: toastId,
        description: `La ruta nace en producción con ${proposal.length} módulos.`,
      })
      router.push(`/ruta/${targetId}`)
    } catch (err) {
      console.error(err)
      toast.error('Error al aprobar la estructura', {
        id: toastId,
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    } finally {
      setApproving(false)
    }
  }

  return (
    <div className="mx-auto max-w-[760px]">
      <Eyebrow tone="primary">Gate 0 · Estructura propuesta · Aprobación humana</Eyebrow>
      <div className="flex items-baseline justify-between">
        <PageTitle>Estructura propuesta</PageTitle>
        <span className="font-mono text-[11px] text-muted-foreground">
          {isLoading ? 'generando...' : `${proposal.length} módulos`}
        </span>
      </div>
      <PageDescription className="mb-5 max-w-none">
        {isLoading 
          ? 'El modelo de lenguaje está estructurando el currículo basado en el material y brief. Esto tomará unos segundos.'
          : 'Arrastra los módulos para reordenarlos. Renombra con ✨ IA, activa o desactiva componentes, o elimina un módulo — sin tocar el resto.'}
      </PageDescription>

      <Card className="gap-0 p-4.5">
        <div className="flex items-center gap-2.5 px-1 pb-3.5">
          <BookMarked className="size-4 text-primary" />
          <span className="font-display text-base text-ink">
            Ruta · {activeRoute?.name || 'Inteligencia avanzada'}
          </span>
          <Badge variant="muted" className="ml-auto">
            {isLoading ? 'generando...' : 'borrador'}
          </Badge>
        </div>
        <Separator className="mb-3.5 bg-secondary" />

        {isLoading ? (
          <div className="flex flex-col gap-2.5">
            <ModuleSkeleton />
            <ModuleSkeleton />
            <ModuleSkeleton />
          </div>
        ) : isFailed ? (
          <FailureState onRegenerate={regenerate} />
        ) : (
          <>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
              <SortableContext items={proposal.map((m) => m.id)} strategy={verticalListSortingStrategy}>
                <div className="flex flex-col gap-2.5">
                  {proposal.map((m, i) => (
                    <ModuleRow key={m.id} m={m} index={i} />
                  ))}
                </div>
              </SortableContext>
            </DndContext>

            <Button
              variant="ghost"
              className="mt-3 w-full border-[1.5px] border-dashed border-input text-primary hover:border-primary hover:bg-card"
              onClick={addProposal}
            >
              <Plus /> Agregar módulo
            </Button>
          </>
        )}
      </Card>

      <Separator className="mt-5.5 mb-5" />
      <div className="flex items-center justify-between gap-4">
        <span className="text-[12.5px] leading-relaxed text-muted-foreground">
          Al aprobar, la ruta nace en <b className="text-ink">borrador</b> con estos módulos en
          este orden.
        </span>
        <div className="flex flex-none gap-3">
          <Button variant="outline" asChild>
            <Link href="/nueva-ruta">Volver</Link>
          </Button>
          <Button onClick={approve} disabled={isLoading || isFailed || approving}>
            {approving ? 'Aprobando...' : 'Aprobar estructura'} <ArrowRight />
          </Button>
        </div>
      </div>
    </div>
  )
}
