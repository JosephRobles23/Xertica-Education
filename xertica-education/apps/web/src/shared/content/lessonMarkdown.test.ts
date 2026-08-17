import { lessonToMarkdown } from './lessonMarkdown'

const lesson = {
  sections: [
    { heading: 'Qué significa razonar', body: 'Descompone el problema en pasos verificables.' },
    { heading: 'Del prompt al plan', body: 'Define el contexto antes de responder.' },
  ],
  terms: [{ term: 'Grounding', def: 'Anclaje de cada afirmación en una fuente verificable.' }],
} as const

const markdown = lessonToMarkdown(lesson)

if (!markdown.includes('## Qué significa razonar')) {
  throw new Error('La lección debe convertirse en secciones Markdown.')
}

if (!markdown.includes('### Glosario') || !markdown.includes('**Grounding**')) {
  throw new Error('La lección debe conservar el glosario en Markdown.')
}

if (!markdown.includes('```concept-map') || !markdown.includes('```flow')) {
  throw new Error('La lección debe incluir bloques visuales para el mapa y el flujo.')
}
