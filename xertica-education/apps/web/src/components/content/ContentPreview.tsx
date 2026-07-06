import type { ContentKind, ContentPack } from '@/lib/types'
import { VideoFrame } from './VideoFrame'
import { InfografiaView } from './InfografiaView'
import { QuizView } from './QuizView'
import { LabView } from './LabView'
import { LessonView } from './LessonView'

/** Renderiza el preview correcto según el tipo de contenido. */
export function ContentPreview({ kind, pack }: { kind: ContentKind; pack: ContentPack }) {
  switch (kind) {
    case 'lesson':
      return <LessonView lesson={pack.lesson} />
    case 'video':
      return <VideoFrame video={pack.video} compact />
    case 'infografia':
      return <InfografiaView info={pack.infografia} compact className="justify-start" />
    case 'quiz':
      return <QuizView quiz={pack.quiz} />
    case 'lab':
      return <LabView lab={pack.lab} />
  }
}
