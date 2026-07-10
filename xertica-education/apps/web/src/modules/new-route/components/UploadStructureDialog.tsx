import { useRef, useState, type ChangeEvent } from 'react'
import { FolderOpen, Upload } from 'lucide-react'
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
import type { UploadedStructure } from '@/shared/store'

/** Dialog para seleccionar la estructura propuesta desde Drive, desde el computador o pegar texto. */
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
  const [text, setText] = useState('')
  const localFileInputRef = useRef<HTMLInputElement | null>(null)

  const submitLocalFile = (file: File) => {
    const value: UploadedStructure = { name: file.name, kind: 'local', localFile: file }
    onSubmit(value)
    toast.success('Estructura recibida', {
      description: `${file.name} · la IA la usará como base de los módulos.`,
    })
    setText('')
    onOpenChange(false)
  }

  const selectDriveFile = async () => {
    try {
      const selected = await pickGoogleDriveFile()
      if (!selected) return
      const value: UploadedStructure = { name: selected.name, kind: 'drive', driveFile: selected }
      onSubmit(value)
      setText('')
      onOpenChange(false)
      toast.success('Estructura recibida', {
        description: `${selected.name} · la IA la usará como base de los módulos.`,
      })
    } catch (err) {
      toast.error('No se pudo abrir Google Drive', {
        description: err instanceof Error ? err.message : 'Error desconocido',
      })
    }
  }

  const selectLocalFile = () => {
    if (localFileInputRef.current) {
      localFileInputRef.current.value = ''
    }
    localFileInputRef.current?.click()
  }

  const handleLocalFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    submitLocalFile(file)
  }

  const submitText = () => {
    if (!text.trim()) return
    const value: UploadedStructure = { name: 'Estructura pegada', kind: 'texto' }
    onSubmit(value)
    toast.success('Estructura recibida', {
      description: `${value.name} · la IA la usará como base de los módulos.`,
    })
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
            Selecciona tu propuesta desde Google Drive, súbela desde tu computador o pégala como
            texto. La IA la usará como base para los módulos.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => setTab(v as 'drive' | 'text')}>
          <TabsList>
            <TabsTrigger value="drive">Google Drive</TabsTrigger>
            <TabsTrigger value="text">Texto</TabsTrigger>
          </TabsList>

          <TabsContent value="drive" className="pt-4">
            <div className="flex flex-col gap-3">
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
              <Button type="button" variant="outline-primary" onClick={selectLocalFile}>
                <Upload /> Subir desde tu computador
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="text" className="pt-4">
            <div className="flex flex-col gap-3">
              <Textarea
                rows={6}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={'Pega aquí la estructura propuesta…\n\nMódulo 1 · …\nMódulo 2 · …'}
              />
              <Button type="button" variant="outline-primary" onClick={selectLocalFile}>
                <Upload /> Cargar archivo desde tu computador
              </Button>
            </div>
          </TabsContent>
        </Tabs>

        <input
          ref={localFileInputRef}
          type="file"
          accept=".doc,.docx,.pdf,.ppt,.pptx,.xls,.xlsx,.txt"
          className="hidden"
          onChange={handleLocalFileChange}
        />

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button disabled={!text.trim()} onClick={submitText}>
            <Upload /> Subir estructura
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
