import type { LessonContent } from '@/shared/lib/types'

export function lessonToMarkdown(lesson: Pick<LessonContent, 'sections' | 'terms'>): string {
  const sectionMarkdown = lesson.sections
    .map((section) => `## ${section.heading}\n\n${section.body.trim()}`)
    .join('\n\n')

  const glossary = lesson.terms.length
    ? `\n\n### Glosario\n\n${lesson.terms.map((term) => `- **${term.term}** — ${term.def}`).join('\n')}`
    : ''

  return [sectionMarkdown, glossary].filter(Boolean).join('\n\n')
}

export function getLessonMarkdown(lesson: LessonContent): string {
  return lesson.markdown?.trim() || lessonToMarkdown(lesson)
}
