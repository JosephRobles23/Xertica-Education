import { useState, type ReactNode } from 'react'
import { Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

/**
 * Popover de refinado: prompt libre para ajustar cualquiera de los
 * 5 tipos de contenido (Lesson, Video, Infografía, Quiz, Laboratorio).
 */
export function RefinePopover({
  label,
  onRefine,
  children,
}: {
  label: string
  onRefine: (prompt: string) => void
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const [prompt, setPrompt] = useState('')

  const submit = () => {
    const value = prompt.trim()
    if (!value) return
    onRefine(value)
    toast.success(`Refinando ${label}…`, {
      description: `“${value.slice(0, 80)}${value.length > 80 ? '…' : ''}”`,
    })
    setPrompt('')
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent align="end" className="w-80">
        <div className="mb-2 flex items-center gap-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-primary">
          <Sparkles className="size-3" />
          Refinar · {label}
        </div>
        <Textarea
          autoFocus
          rows={3}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
          }}
          placeholder={`Escribe cómo quieres refinar el contenido de ${label}…`}
          className="text-[13px]"
        />
        <div className="mt-3 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button size="sm" disabled={!prompt.trim()} onClick={submit}>
            <Sparkles className="size-3.5" /> Refinar
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
