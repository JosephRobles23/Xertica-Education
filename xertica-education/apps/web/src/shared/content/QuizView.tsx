import { useState } from 'react'
import { Check, Plus, RotateCcw, Sparkles, Trash2, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/shared/ui/button'
import { cn } from '@/shared/lib/utils'
import type { QuizContent, QuizQuestion } from '@/shared/lib/types'

export function QuizView({ quiz, className }: { quiz: QuizContent; className?: string }) {
  const [questions, setQuestions] = useState<QuizQuestion[]>([...quiz.questions])
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [done, setDone] = useState(false)
  const [adding, setAdding] = useState(false)
  const [newQ, setNewQ] = useState('')
  const [newOpts, setNewOpts] = useState(['', '', ''])
  const [newCorrect, setNewCorrect] = useState(0)

  const total = questions.length
  const answered = Object.keys(answers).length
  const score = questions.reduce(
    (n, q, i) => n + (answers[i] === q.correct ? 1 : 0),
    0,
  )

  const submit = () => {
    setDone(true)
    toast[score === total ? 'success' : 'info'](
      `Resultado: ${score} de ${total} correctas`,
      { description: score === total ? '¡Dominio completo!' : 'Revisa las marcadas en rojo y reintenta.' },
    )
  }

  const reset = () => {
    setAnswers({})
    setDone(false)
  }

  const refineQuestion = (qi: number) => {
    toast.loading('Refinando pregunta con IA…', { id: `refine-${qi}` })
    window.setTimeout(() => {
      setQuestions((prev) => {
        const next = [...prev]
        const q = next[qi]
        if (!q) return prev
        next[qi] = { ...q, q: q.q + ' (refinada por IA)' }
        return next
      })
      toast.success('Pregunta refinada', {
        id: `refine-${qi}`,
        description: 'La IA ajustó la redacción para mayor claridad.',
      })
    }, 800)
  }

  const addQuestion = () => {
    if (!newQ.trim() || newOpts.some((o) => !o.trim())) {
      toast.error('Completa todos los campos')
      return
    }
    setQuestions((prev) => [
      ...prev,
      { q: newQ.trim(), opts: [newOpts[0]!.trim(), newOpts[1]!.trim(), newOpts[2]!.trim()], correct: newCorrect as 0 | 1 | 2 },
    ])
    setNewQ('')
    setNewOpts(['', '', ''])
    setNewCorrect(0)
    setAdding(false)
    setDone(false)
    setAnswers({})
    toast.success('Pregunta agregada')
  }

  const removeQuestion = (qi: number) => {
    setQuestions((prev) => prev.filter((_, i) => i !== qi))
    setAnswers({})
    setDone(false)
    toast.info('Pregunta eliminada')
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {questions.map((q, qi) => (
        <div key={qi} className="rounded-xl border-[1.5px] bg-card p-4.5">
          <div className="mb-3 flex gap-2.5">
            <span className="font-mono text-xs font-semibold text-primary">
              {String(qi + 1).padStart(2, '0')}
            </span>
            <span className="flex-1 text-sm font-medium leading-snug text-ink">{q.q}</span>
            {!done && (
              <div className="flex shrink-0 gap-1">
                <button
                  type="button"
                  onClick={() => refineQuestion(qi)}
                  className="flex size-6 cursor-pointer items-center justify-center rounded-md text-primary transition-colors outline-none hover:bg-primary/10 focus-visible:ring-[3px] focus-visible:ring-ring/30"
                  title="Refinar con IA"
                >
                  <Sparkles className="size-3.5" />
                </button>
                {questions.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeQuestion(qi)}
                    className="flex size-6 cursor-pointer items-center justify-center rounded-md text-destructive transition-colors outline-none hover:bg-destructive/10 focus-visible:ring-[3px] focus-visible:ring-ring/30"
                    title="Eliminar pregunta"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2">
            {q.opts.map((opt, oi) => {
              const picked = answers[qi] === oi
              const isCorrect = oi === q.correct
              const showCorrect = done && isCorrect
              const showWrong = done && picked && !isCorrect

              return (
                <button
                  key={oi}
                  type="button"
                  disabled={done}
                  onClick={() => setAnswers((a) => ({ ...a, [qi]: oi }))}
                  className={cn(
                    'flex cursor-pointer items-center gap-3 rounded-lg border-[1.5px] px-3.5 py-2.5 text-left text-[13.5px] transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/30',
                    'disabled:cursor-default',
                    showCorrect
                      ? 'border-success bg-success/10 text-ink'
                      : showWrong
                        ? 'border-destructive bg-destructive/8 text-ink'
                        : picked
                          ? 'border-primary bg-primary/8 text-ink'
                          : 'border-border bg-card hover:border-input',
                  )}
                >
                  <span
                    className={cn(
                      'flex size-5 shrink-0 items-center justify-center rounded-full border-[1.5px] font-mono text-[11px] font-bold',
                      showCorrect
                        ? 'border-success text-success'
                        : showWrong
                          ? 'border-destructive text-destructive'
                          : picked
                            ? 'border-primary text-primary'
                            : 'border-input text-input',
                    )}
                  >
                    {showCorrect ? (
                      <Check className="size-3" strokeWidth={3} />
                    ) : showWrong ? (
                      <X className="size-3" strokeWidth={3} />
                    ) : (
                      String.fromCharCode(65 + oi)
                    )}
                  </span>
                  {opt}
                </button>
              )
            })}
          </div>
        </div>
      ))}

      {/* Formulario para agregar pregunta */}
      {adding && (
        <div className="rounded-xl border-[1.5px] border-primary bg-primary/5 p-4.5">
          <div className="mb-3 flex items-center gap-2">
            <Plus className="size-4 text-primary" />
            <span className="text-[13.5px] font-semibold text-ink">Nueva pregunta</span>
          </div>
          <input
            type="text"
            placeholder="Escribe la pregunta…"
            value={newQ}
            onChange={(e) => setNewQ(e.target.value)}
            className="mb-3 w-full rounded-lg border-[1.5px] border-border bg-card px-3.5 py-2.5 text-[13.5px] outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
          />
          <div className="mb-3 flex flex-col gap-2">
            {newOpts.map((opt, oi) => (
              <div key={oi} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setNewCorrect(oi)}
                  className={cn(
                    'flex size-5 shrink-0 cursor-pointer items-center justify-center rounded-full border-[1.5px] font-mono text-[11px] font-bold transition-colors',
                    newCorrect === oi
                      ? 'border-success bg-success/15 text-success'
                      : 'border-input text-input',
                  )}
                >
                  {newCorrect === oi ? <Check className="size-3" strokeWidth={3} /> : String.fromCharCode(65 + oi)}
                </button>
                <input
                  type="text"
                  placeholder={`Opción ${String.fromCharCode(65 + oi)}`}
                  value={opt}
                  onChange={(e) => {
                    const next = [...newOpts]
                    next[oi] = e.target.value
                    setNewOpts(next)
                  }}
                  className="flex-1 rounded-lg border-[1.5px] border-border bg-card px-3 py-2 text-[13px] outline-none transition-colors placeholder:text-muted-foreground focus:border-primary"
                />
              </div>
            ))}
          </div>
          <p className="mb-3 text-[11px] text-muted-foreground">
            Haz clic en la letra para marcar la respuesta correcta.
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={addQuestion}>
              <Plus /> Agregar
            </Button>
            <Button variant="outline" size="sm" onClick={() => setAdding(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] text-muted-foreground">
          {done ? `Puntaje: ${score}/${total}` : `${answered}/${total} respondidas`}
        </span>
        <div className="flex gap-2">
          {!done && !adding && (
            <Button variant="outline" size="sm" onClick={() => setAdding(true)}>
              <Plus /> Agregar pregunta
            </Button>
          )}
          {done ? (
            <Button variant="outline" size="sm" onClick={reset}>
              <RotateCcw /> Reintentar
            </Button>
          ) : (
            <Button size="sm" disabled={answered < total} onClick={submit}>
              Enviar respuestas
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
