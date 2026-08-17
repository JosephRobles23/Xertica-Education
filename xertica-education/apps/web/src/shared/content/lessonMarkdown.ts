import type { LessonContent } from '@/shared/lib/types'

export function lessonToMarkdown(lesson: Pick<LessonContent, 'sections' | 'terms'>): string {
  const sectionMarkdown = lesson.sections
    .map((section) => `## ${section.heading}\n\n${section.body.trim()}`)
    .join('\n\n')

  const labels = lesson.sections.map((section) => section.heading).join(' | ')
  const glossary = lesson.terms.length
    ? `\n\n### Glosario\n\n${lesson.terms.map((term) => `- **${term.term}** — ${term.def}`).join('\n')}`
    : ''

  return [
    sectionMarkdown,
    '### Mapa de conceptos',
    '',
    '```concept-map',
    `core: ${lesson.sections[0]?.heading ?? 'Lección'}`,
    `branches: ${labels}`,
    '```',
    '',
    '### Flujo de aprendizaje',
    '',
    '```flow',
    `steps: ${labels}`,
    '```',
    glossary,
  ]
    .filter(Boolean)
    .join('\n\n')
}

export function getLessonMarkdown(lesson: LessonContent): string {
  return lesson.markdown?.trim() || lessonToMarkdown(lesson)
}
