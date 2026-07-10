import type { ContentKind, ContentPack } from '@/shared/lib/types'
import { VideoFrame } from './VideoFrame'
import { InfografiaView } from './InfografiaView'
import { QuizView } from './QuizView'
import { LabView } from './LabView'
import { LessonView } from './LessonView'

export function ContentPreview({
  kind,
  pack,
  videoUrl,
  compact,
  routeId,
  moduleId,
}: {
  kind: ContentKind
  pack: ContentPack
  videoUrl?: string
  compact?: boolean
  routeId?: string
  moduleId?: string
}) {
  switch (kind) {
    case 'lesson':
      return <LessonView lesson={pack.lesson} routeId={routeId} moduleId={moduleId} />
    case 'video':
      return <VideoFrame video={pack.video} videoUrl={videoUrl} compact={compact} />
    case 'infografia':
      return <InfografiaView info={pack.infografia} className="justify-start" routeId={routeId} moduleId={moduleId} />
    case 'quiz':
      return <QuizView quiz={pack.quiz} routeId={routeId} moduleId={moduleId} />
    case 'lab':
      return <LabView lab={pack.lab} />
  }
}
