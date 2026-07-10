import { useState } from 'react'
import { FileText, FolderOpen, Upload, X } from 'lucide-react'
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
import { pickGoogleDriveFile } from '@/shared/lib/googleDrive'
import type { GoogleDriveSelection } from '@/shared/lib/googleDrive'
import type { UploadedStructure } from '@/shared/store'

/** Dialog para seleccionar la estructura propuesta desde Drive o pegar texto. */
export function UploadStructureDialog({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (v: UploadedStructure) => void
}) {
  const [tab, setTab] = useState<'drive' | 'text'>('drive')
  const [driveFile, setDriveFile] = useState<GoogleDriveSelection | null>(null)
  const [text, setText] = useState('')

  const canSubmit = tab === 'drive' ? driveFile !== null : text.trim().length > 0

  const selectDriveFile = async () => {
    try {
      const selected = await pickGoogleDriveFile()
      if (!selected) return
      setDriveFile(selected)
      toast.success('Estructura seleccionada desde Drive', {
        description: selected.name,
      })
    } catch (err) {
      toast.error('No se pudo abrir Google Drive', {
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    }
  }

  const submit = () => {
    if (!canSubmit) return
    const value: UploadedStructure =
      tab === 'drive' && driveFile
        ? { name: driveFile.name, kind: 'drive', driveFile }
        : { name: 'Estructura pegada', kind: 'texto' }
    onSubmit(value)
    toast.success('Estructura recibida', {
      description: `${value.name} · la IA la usará como base de los módulos.`,
    })
    setDriveFile(null)
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
            Selecciona tu propuesta de estructura desde Google Drive o pégala como texto. La IA la
            usará como base para los módulos.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => setTab(v as 'drive' | 'text')}>
          <TabsList>
            <TabsTrigger value="drive">Google Drive</TabsTrigger>
            <TabsTrigger value="text">Texto</TabsTrigger>
          </TabsList>

          <TabsContent value="drive" className="pt-4">
            <button
              type="button"
              onClick={selectDriveFile}
              className="w-full cursor-pointer rounded-xl border-[1.5px] border-dashed border-input bg-background/60 p-7 text-center transition-colors outline-none hover:border-primary focus-visible:ring-[3px] focus-visible:ring-ring/30"
            >
              <FolderOpen className="mx-auto mb-2 size-5 text-muted-foreground" />
              <div className="text-[13.5px]">Selecciona una estructura desde Google Drive</div>
              <div className="mt-1 font-mono text-[10.5px] text-muted-foreground">
                DOCX · PDF · TXT
              </div>
            </button>
            {driveFile && (
              <div className="mt-3 flex items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5">
                <FileText className="size-4 text-primary" />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] text-ink">{driveFile.name}</div>
                  <div className="font-mono text-[10.5px] text-muted-foreground">
                    Google Drive · listo para importar
                  </div>
                </div>
                <Button variant="ghost" size="icon" className="size-7" onClick={() => setDriveFile(null)}>
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
