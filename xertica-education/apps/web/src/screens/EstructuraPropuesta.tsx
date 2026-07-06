'use client'

import { useState } from 'react'
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
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Eyebrow, PageDescription, PageTitle } from '@/components/PageHeader'
import { CONTENT_KINDS, KIND_LABEL, type ProposalModule } from '@/lib/types'
import { useStore } from '@/store'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'

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

export default function EstructuraPropuesta() {
  const router = useRouter()
  const { proposal, reorderProposal, addProposal, activeRouteId, fetchRoutes } = useStore()
  const [approving, setApproving] = useState(false)

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
    const toastId = toast.loading('Aprobando estructura y configurando ruta...')
    try {
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
          {proposal.length} módulos
        </span>
      </div>
      <PageDescription className="mb-5 max-w-none">
        <b className="text-foreground">Arrastra</b> los módulos para reordenarlos. Renombra con ✨
        IA, activa o desactiva componentes, o elimina un módulo — sin tocar el resto.
      </PageDescription>

      <Card className="gap-0 p-4.5">
        <div className="flex items-center gap-2.5 px-1 pb-3.5">
          <BookMarked className="size-4 text-primary" />
          <span className="font-display text-base text-ink">Ruta · Inteligencia avanzada</span>
          <Badge variant="muted" className="ml-auto">
            borrador
          </Badge>
        </div>
        <Separator className="mb-3.5 bg-secondary" />

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
          <Button onClick={approve} disabled={approving}>
            {approving ? 'Aprobando...' : 'Aprobar estructura'} <ArrowRight />
          </Button>
        </div>
      </div>
    </div>
  )
}
