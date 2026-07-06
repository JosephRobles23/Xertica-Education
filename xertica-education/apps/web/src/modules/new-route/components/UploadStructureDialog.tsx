import { useRef, useState } from 'react'
import { FileText, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Textarea } from '@/shared/ui/textarea'
import type { UploadedStructure } from '@/shared/store'

/** Dialog para subir la estructura propuesta (DOCX, PDF o texto). */
export function UploadStructureDialog({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (v: UploadedStructure) => void
}) {
  const [tab, setTab] = useState<'file' | 'text'>('file')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const canSubmit = tab === 'file' ? file !== null : text.trim().length > 0

  const submit = () => {
    if (!canSubmit) return
    const value: UploadedStructure =
      tab === 'file' && file
        ? { name: file.name, kind: 'archivo' }
        : { name: 'Estructura pegada', kind: 'texto' }
    onSubmit(value)
    toast.success('Estructura recibida', {
      description: `${value.name} · la IA la usará como base de los módulos.`,
    })
    setFile(null)
    setText('')
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <div className="font-mono text-[10px] font-semibold uppercase tracking-[0.1em] text-primary">
            Estructura de ruta de aprendizaje
          </div>
          <DialogTitle>Subir estructura propuesta</DialogTitle>
          <DialogDescription>
            Sube tu propuesta de estructura como DOCX o PDF, o pégala como texto. La IA la usará
            como base para los módulos.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => setTab(v as 'file' | 'text')}>
          <TabsList>
            <TabsTrigger value="file">Archivo</TabsTrigger>
            <TabsTrigger value="text">Texto</TabsTrigger>
          </TabsList>

          <TabsContent value="file" className="pt-4">
            <input
              ref={inputRef}
              type="file"
              accept=".docx,.pdf,.txt"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="w-full cursor-pointer rounded-xl border-[1.5px] border-dashed border-input bg-background/60 p-7 text-center transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
            >
              <Upload className="mx-auto mb-2 size-5 text-muted-foreground" />
              <div className="text-[13.5px]">Arrastra o selecciona un archivo</div>
              <div className="mt-1 font-mono text-[10.5px] text-muted-foreground">
                DOCX · PDF · TXT
              </div>
            </button>
            {file && (
              <div className="mt-3 flex items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5">
                <FileText className="size-4 text-primary" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] text-ink">{file.name}</div>
                  <div className="font-mono text-[10.5px] text-muted-foreground">
                    listo para procesar
                  </div>
                </div>
                <Button variant="ghost" size="icon" className="size-7" onClick={() => setFile(null)}>
                  <X className="size-3.5" />
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="text" className="pt-4">
            <Textarea
              rows={6}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={'Pega aquí la estructura propuesta…\n\nMódulo 1 · …\nMódulo 2 · …'}
            />
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button disabled={!canSubmit} onClick={submit}>
            <Upload /> Subir estructura
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
