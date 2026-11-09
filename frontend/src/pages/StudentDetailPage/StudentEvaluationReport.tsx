import autoTable from 'jspdf-autotable'
import { Download } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { createStudentEvaluation, listStudentEvaluations } from '@/features/students/evaluationsApi'
import type { StudentDetail } from '@/entities/student/types'
import { STUDENT_STATUS_LABELS } from '@/entities/student/types'
import type { StudentEvaluation } from '@/entities/studentEvaluation/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { addPdfFooter, createBrandedPdf, PDF_TABLE_THEME } from '@/shared/lib/pdf'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'

const scoreLabels: Array<[keyof StudentEvaluation, string]> = [
  ['performance_score', 'Desempenho'],
  ['evolution_score', 'Evolução'],
  ['interaction_score', 'Interação'],
  ['participation_score', 'Participação'],
  ['autonomy_score', 'Autonomia'],
  ['wellbeing_score', 'Bem-estar'],
]

export function StudentEvaluationReport({ student }: { student: StudentDetail }) {
  const [items, setItems] = useState<StudentEvaluation[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      const result = await listStudentEvaluations(student.id)
      setItems(result.items)
      setError(null)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setLoading(false)
    }
  }, [student.id])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca inicial do historico ao abrir a aba
    void reload()
  }, [reload])

  function downloadPdf() {
    const doc = createBrandedPdf(`Relatório de ${student.full_name}`, `${items.length} avaliação${items.length === 1 ? '' : 'ões'} registrada${items.length === 1 ? '' : 's'}`)
    autoTable(doc, {
      startY: 34,
      margin: { left: 14, right: 14 },
      head: [['Situação cadastral', 'Idade', 'Responsável principal']],
      body: [[
        STUDENT_STATUS_LABELS[student.status],
        student.age != null ? `${student.age} anos` : 'Não informada',
        student.guardian?.full_name ?? 'Não informado',
      ]],
      ...PDF_TABLE_THEME,
    })

    let cursorY = (doc as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? 50
    const pageWidth = doc.internal.pageSize.getWidth()
    const pageHeight = doc.internal.pageSize.getHeight()

    for (const evaluation of items) {
      if (cursorY > pageHeight - 70) {
        doc.addPage()
        cursorY = 20
      }
      cursorY += 10
      doc.setFont('courier', 'bold')
      doc.setFontSize(10)
      doc.setTextColor(17, 17, 17)
      doc.text(`${evaluation.period_start} -> ${evaluation.period_end}  ·  Apoio ${evaluation.support_level}`, 14, cursorY)

      autoTable(doc, {
        startY: cursorY + 4,
        margin: { left: 14, right: 14 },
        head: [scoreLabels.map(([, label]) => label)],
        body: [scoreLabels.map(([key]) => String(evaluation[key] as number))],
        ...PDF_TABLE_THEME,
      })
      cursorY = (doc as unknown as { lastAutoTable?: { finalY: number } }).lastAutoTable?.finalY ?? cursorY + 20

      const notes: Array<[string, string]> = [
        ['Observações', evaluation.observations],
        ['Estratégias eficazes', evaluation.effective_strategies],
        ['Próximo objetivo', evaluation.next_objective],
      ]
      doc.setFont('courier', 'normal')
      doc.setFontSize(8.5)
      doc.setTextColor(60, 60, 60)
      for (const [label, value] of notes) {
        cursorY += 7
        doc.setFont('courier', 'bold')
        doc.text(`${label}:`, 14, cursorY)
        doc.setFont('courier', 'normal')
        const wrapped = doc.splitTextToSize(value, pageWidth - 28)
        doc.text(wrapped, 14, cursorY + 4)
        cursorY += 4 + wrapped.length * 4
      }
    }

    addPdfFooter(doc)
    doc.save(`relatorio-${student.full_name.toLowerCase().replace(/[^\w]+/g, '-')}.pdf`)
  }

  return (
    <div className="student-report space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-green">
            Acompanhamento individual
          </p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-white">
            Relatório de {student.full_name}
          </h2>
          <p className="mt-2 text-sm text-white/45">
            Escala contextual, observações e estratégias — sem comparação entre estudantes.
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={downloadPdf}>
          <Download className="h-4 w-4" aria-hidden="true" /> Exportar PDF
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <ReportFact label="Situação cadastral" value={STUDENT_STATUS_LABELS[student.status]} />
        <ReportFact label="Idade" value={student.age != null ? `${student.age} anos` : 'Não informada'} />
        <ReportFact
          label="Responsável principal"
          value={student.guardian?.full_name ?? 'Não informado'}
        />
      </div>

      <div className="flex flex-col gap-4 border-y border-white/10 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-display text-sm font-semibold text-white">Avaliações registradas</p>
          <p className="mt-1 text-xs text-white/45">
            Desempenho, evolução, interação, participação, autonomia e bem-estar.
          </p>
        </div>
        <Button onClick={() => setOpen((value) => !value)}>
          {open ? 'Fechar avaliação' : 'Lançar avaliação'}
        </Button>
      </div>

      {open && (
        <EvaluationForm
          studentId={student.id}
          onSaved={() => {
            setOpen(false)
            void reload()
          }}
        />
      )}

      {error && <p className="border border-danger/40 p-4 text-sm text-danger">{error}</p>}

      {loading ? (
        <p className="text-sm text-white/45">Carregando histórico…</p>
      ) : items.length === 0 ? (
        <div className="border border-dashed border-white/15 p-5">
          <p className="text-sm text-white/55">Nenhuma avaliação lançada ainda.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <EvaluationCard key={item.id} evaluation={item} />
          ))}
        </div>
      )}
    </div>
  )
}

function EvaluationCard({ evaluation }: { evaluation: StudentEvaluation }) {
  return (
    <article className="border border-white/10 p-5">
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <p className="font-display text-sm font-semibold text-white">
            {evaluation.period_start} → {evaluation.period_end}
          </p>
          <p className="mt-1 text-xs uppercase tracking-[0.12em] text-brand-green">
            Apoio {evaluation.support_level}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
          {scoreLabels.map(([key, label]) => (
            <div key={key} className="border border-white/10 px-2 py-2 text-center">
              <p className="text-[10px] text-white/40">{label}</p>
              <p className="mt-1 font-display text-lg text-white">{evaluation[key] as number}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-5 grid gap-4 border-t border-white/10 pt-4 md:grid-cols-3">
        <ReportText label="Observações" value={evaluation.observations} />
        <ReportText label="Estratégias eficazes" value={evaluation.effective_strategies} />
        <ReportText label="Próximo objetivo" value={evaluation.next_objective} />
      </div>
    </article>
  )
}

function ReportText({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.12em] text-white/35">{label}</p>
      <p className="mt-2 text-sm leading-6 text-white/65">{value}</p>
    </div>
  )
}

function ReportFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-white/10 bg-white/[.02] p-4">
      <p className="text-xs uppercase tracking-[0.12em] text-white/35">{label}</p>
      <p className="mt-3 font-semibold text-white">{value}</p>
    </div>
  )
}

interface EvaluationFormState {
  period_start: string
  period_end: string
  performance_score: number
  evolution_score: number
  interaction_score: number
  participation_score: number
  autonomy_score: number
  wellbeing_score: number
  support_level: string
  observations: string
  effective_strategies: string
  next_objective: string
}

function EvaluationForm({ studentId, onSaved }: { studentId: string; onSaved: () => void }) {
  const today = new Date().toISOString().slice(0, 10)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<EvaluationFormState>({
    period_start: today,
    period_end: today,
    performance_score: 5,
    evolution_score: 5,
    interaction_score: 5,
    participation_score: 5,
    autonomy_score: 5,
    wellbeing_score: 5,
    support_level: 'moderado',
    observations: '',
    effective_strategies: '',
    next_objective: '',
  })

  function setField<K extends keyof EvaluationFormState>(key: K, value: EvaluationFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      await createStudentEvaluation(studentId, form)
      onSaved()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="border border-brand-green/40 bg-brand-green/[.03] p-5">
      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Início do período"
          type="date"
          value={form.period_start}
          onChange={(event) => setField('period_start', event.target.value)}
        />
        <Input
          label="Fim do período"
          type="date"
          value={form.period_end}
          onChange={(event) => setField('period_end', event.target.value)}
        />
      </div>
      <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3">
        {scoreLabels.map(([key, label]) => (
          <Select
            key={key}
            label={label}
            value={form[key as keyof EvaluationFormState] as number}
            onChange={(event) =>
              setField(key as keyof EvaluationFormState, Number(event.target.value) as never)
            }
            options={Array.from({ length: 10 }, (_, index) => ({
              value: String(index + 1),
              label: String(index + 1),
            }))}
          />
        ))}
      </div>
      <div className="mt-4">
        <Select
          label="Nível de apoio"
          value={form.support_level}
          onChange={(event) => setField('support_level', event.target.value)}
          options={[
            { value: 'intenso', label: 'Intenso' },
            { value: 'moderado', label: 'Moderado' },
            { value: 'leve', label: 'Leve' },
            { value: 'independente', label: 'Independente' },
          ]}
        />
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {(
          [
            ['observations', 'Observações'],
            ['effective_strategies', 'Estratégias eficazes'],
            ['next_objective', 'Próximo objetivo'],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="text-xs text-white/55">
            {label}
            <textarea
              required
              minLength={10}
              className="mt-2 min-h-28 w-full border border-white/15 bg-black p-3 text-sm text-white"
              value={form[key]}
              onChange={(event) => setField(key, event.target.value)}
            />
          </label>
        ))}
      </div>
      {error && <p className="mt-4 text-sm text-danger">{error}</p>}
      <Button type="submit" loading={saving} className="mt-5">
        Salvar avaliação
      </Button>
    </form>
  )
}
