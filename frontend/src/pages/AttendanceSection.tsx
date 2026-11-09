import { CalendarCheck, ChevronDown, ClipboardList, History, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'

import {
  getAttendanceSessionMarks,
  getAttendanceSummary,
  listAttendanceSessions,
  openAttendanceSession,
  recordAttendanceMarks,
} from '@/features/attendance/api'
import { listEnrollments } from '@/features/enrollments/api'
import { getStudentNames } from '@/features/students/api'
import type {
  AttendanceMark,
  AttendanceMarkStatus,
  AttendanceMonthlySummary,
  AttendanceSessionSummary,
} from '@/entities/attendance/types'
import { ATTENDANCE_MARK_LABELS } from '@/entities/attendance/types'
import type { Enrollment } from '@/entities/enrollment/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { Button } from '@/shared/ui/Button'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Input } from '@/shared/ui/Input'
import { StatusBadge } from '@/shared/ui/StatusBadge'

type View = 'chamada' | 'historico' | 'resumo'

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

export function AttendanceSection({
  classId,
  canTakeAttendance,
  showHeader = true,
}: {
  classId: string
  canTakeAttendance: boolean
  showHeader?: boolean
}) {
  const [view, setView] = useState<View>('chamada')

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {showHeader ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/35">Frequência</p>
            <h2 className="mt-1 font-display text-xl font-semibold text-white">Chamada</h2>
            <p className="mt-1 text-xs text-white/45">
              Chamadas ficam detalhadas por até 6 meses; depois disso viram um resumo mensal por estudante.
            </p>
          </div>
        ) : (
          <div />
        )}
        <div className="flex gap-2">
          <Button type="button" size="sm" variant={view === 'chamada' ? 'primary' : 'secondary'} onClick={() => setView('chamada')}>
            <CalendarCheck className="h-3.5 w-3.5" aria-hidden="true" /> Tirar chamada
          </Button>
          <Button type="button" size="sm" variant={view === 'historico' ? 'primary' : 'secondary'} onClick={() => setView('historico')}>
            <History className="h-3.5 w-3.5" aria-hidden="true" /> Histórico
          </Button>
          <Button type="button" size="sm" variant={view === 'resumo' ? 'primary' : 'secondary'} onClick={() => setView('resumo')}>
            <ClipboardList className="h-3.5 w-3.5" aria-hidden="true" /> Resumo mensal
          </Button>
        </div>
      </div>

      {view === 'chamada' && <TakeAttendance classId={classId} canTakeAttendance={canTakeAttendance} />}
      {view === 'historico' && <AttendanceHistory classId={classId} />}
      {view === 'resumo' && <AttendanceSummaryView classId={classId} />}
    </div>
  )
}

interface MarkDraft {
  status: AttendanceMarkStatus | ''
  note: string
}

function TakeAttendance({ classId, canTakeAttendance }: { classId: string; canTakeAttendance: boolean }) {
  const [date, setDate] = useState(todayISO())
  const [enrollments, setEnrollments] = useState<Enrollment[]>([])
  const [studentNames, setStudentNames] = useState<Record<string, string>>({})
  const [drafts, setDrafts] = useState<Record<string, MarkDraft>>({})
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    listEnrollments({ classId, status: 'ativa', page: 1, pageSize: 100, signal: controller.signal })
      .then((page) => {
        setEnrollments(page.items)
        return getStudentNames(page.items.map((item) => item.student_id), controller.signal)
      })
      .then((result) => setStudentNames(result.names))
      .catch(() => {})
    return () => controller.abort()
  }, [classId])

  useEffect(() => {
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)
    setSaved(false)
    listAttendanceSessions(classId, 100, 0, controller.signal)
      .then((page) => page.items.find((item) => item.session_date === date) ?? null)
      .then((existing) => {
        if (!existing) {
          setSessionId(null)
          setDrafts({})
          return
        }
        setSessionId(existing.id)
        return getAttendanceSessionMarks(existing.id, controller.signal).then((marks) => {
          setDrafts(
            Object.fromEntries(
              marks.map((mark) => [mark.enrollment_id, { status: mark.status, note: mark.note ?? '' }]),
            ),
          )
        })
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [classId, date])

  function setDraft(enrollmentId: string, patch: Partial<MarkDraft>) {
    setDrafts((current) => ({
      ...current,
      [enrollmentId]: { status: current[enrollmentId]?.status ?? '', note: current[enrollmentId]?.note ?? '', ...patch },
    }))
  }

  async function handleSave() {
    setError(null)
    setSaved(false)
    const unmarked = enrollments.filter((enrollment) => !drafts[enrollment.id]?.status)
    if (unmarked.length > 0) {
      setError('Marque a presença de todos os estudantes antes de salvar.')
      return
    }
    const invalidJustified = enrollments.find((enrollment) => {
      const draft = drafts[enrollment.id]
      return draft?.status === 'justificada' && draft.note.trim().length < 3
    })
    if (invalidJustified) {
      setError('Toda falta justificada precisa de uma observação.')
      return
    }

    setSaving(true)
    try {
      let activeSessionId = sessionId
      if (!activeSessionId) {
        const session = await openAttendanceSession(classId, date)
        activeSessionId = session.id
        setSessionId(session.id)
      }
      await recordAttendanceMarks(
        activeSessionId,
        enrollments.map((enrollment) => ({
          enrollment_id: enrollment.id,
          status: drafts[enrollment.id].status as AttendanceMarkStatus,
          note: drafts[enrollment.id].status === 'justificada' ? drafts[enrollment.id].note.trim() : undefined,
        })),
      )
      setSaved(true)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="liquid-glass flex flex-wrap items-end gap-4 border-t-2 border-t-brand-green/50 p-4">
        <Input
          label="Data da aula"
          type="date"
          value={date}
          max={todayISO()}
          onChange={(event) => setDate(event.target.value)}
          className="max-w-xs"
        />
        {sessionId && <StatusBadge label="Chamada já registrada nesta data" tone="success" />}
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-10 text-sm text-white/50">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Carregando turma…
        </div>
      )}

      {!loading && enrollments.length === 0 && (
        <EmptyState icon={CalendarCheck} title="Sem estudantes ativos" description="Matricule estudantes nesta turma para começar a tirar chamada." />
      )}

      {!loading && enrollments.length > 0 && (
        <fieldset disabled={!canTakeAttendance || saving} className="flex flex-col gap-2 disabled:opacity-60">
          {enrollments.map((enrollment, index) => {
            const draft = drafts[enrollment.id] ?? { status: '', note: '' }
            return (
              <div key={enrollment.id} className="liquid-glass flex flex-col gap-3 border-l-2 border-l-white/10 px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-4">
                    <span className="font-display text-xs text-white/30">{String(index + 1).padStart(2, '0')}</span>
                    <span className="text-sm text-white">{studentNames[enrollment.student_id] ?? 'Carregando…'}</span>
                  </span>
                  <div className="relative">
                    <select
                      value={draft.status}
                      onChange={(event) => setDraft(enrollment.id, { status: event.target.value as AttendanceMarkStatus })}
                      className="h-9 min-w-[11rem] appearance-none border border-white/15 bg-white/5 pl-3 pr-9 text-sm text-white outline-none transition focus:border-brand-green focus:bg-white/8"
                    >
                      <option value="" disabled className="bg-surface">Marcar presença…</option>
                      {(Object.entries(ATTENDANCE_MARK_LABELS) as Array<[AttendanceMarkStatus, string]>).map(([value, label]) => (
                        <option key={value} value={value} className="bg-surface">{label}</option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-white/40" aria-hidden="true" />
                  </div>
                </div>
                {draft.status === 'justificada' && (
                  <Input
                    label="Motivo da falta justificada"
                    value={draft.note}
                    onChange={(event) => setDraft(enrollment.id, { note: event.target.value })}
                    hint="Pelo menos 3 caracteres."
                  />
                )}
              </div>
            )
          })}
        </fieldset>
      )}

      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      {saved && !error && <p className="text-sm text-brand-green">Chamada salva.</p>}

      {canTakeAttendance && enrollments.length > 0 && (
        <Button type="button" onClick={() => void handleSave()} loading={saving}>
          {saving ? 'Salvando…' : 'Salvar chamada'}
        </Button>
      )}
    </div>
  )
}

function AttendanceHistory({ classId }: { classId: string }) {
  const [sessions, setSessions] = useState<AttendanceSessionSummary[] | null>(null)
  const [studentNames, setStudentNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openSessionId, setOpenSessionId] = useState<string | null>(null)
  const [marksBySession, setMarksBySession] = useState<Record<string, AttendanceMark[]>>({})
  const [marksLoading, setMarksLoading] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      listAttendanceSessions(classId, 100, 0, controller.signal),
      listEnrollments({ classId, page: 1, pageSize: 100, signal: controller.signal }),
    ])
      .then(([sessionPage, enrollmentPage]) => {
        setSessions(sessionPage.items)
        const byEnrollment = Object.fromEntries(enrollmentPage.items.map((item) => [item.id, item.student_id]))
        return getStudentNames(Object.values(byEnrollment), controller.signal).then((result) => ({
          names: result.names,
          byEnrollment,
        }))
      })
      .then(({ names, byEnrollment }) => {
        setStudentNames(
          Object.fromEntries(
            Object.entries(byEnrollment).map(([enrollmentId, studentId]) => [enrollmentId, names[studentId] ?? 'Estudante']),
          ),
        )
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [classId])

  async function toggleSession(sessionId: string) {
    if (openSessionId === sessionId) {
      setOpenSessionId(null)
      return
    }
    setOpenSessionId(sessionId)
    if (marksBySession[sessionId]) return
    setMarksLoading(true)
    try {
      const marks = await getAttendanceSessionMarks(sessionId)
      setMarksBySession((current) => ({ ...current, [sessionId]: marks }))
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setMarksLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-sm text-white/50">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        Carregando histórico…
      </div>
    )
  }

  if (error) return <p className="text-sm text-danger">{error}</p>

  if (!sessions || sessions.length === 0) {
    return <EmptyState icon={History} title="Nenhuma chamada registrada ainda" description="Chamadas feitas nos últimos 6 meses aparecem aqui, dia a dia." />
  }

  return (
    <ul className="flex flex-col gap-2">
      {sessions.map((session) => {
        const marks = marksBySession[session.id]
        const presentCount = marks?.filter((mark) => mark.status === 'presente').length ?? null
        return (
          <li key={session.id} className="liquid-glass border-l-2 border-l-white/10">
            <button
              type="button"
              onClick={() => void toggleSession(session.id)}
              className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 text-left transition hover:border-l-brand-green"
            >
              <span className="text-sm text-white">
                {new Date(`${session.session_date}T00:00:00`).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })}
              </span>
              <span className="flex items-center gap-3">
                {presentCount !== null && <span className="text-xs text-white/45">{presentCount}/{marks?.length ?? 0} presentes</span>}
                <StatusBadge label={session.status === 'fechada' ? 'Fechada' : 'Editável'} tone={session.status === 'fechada' ? 'neutral' : 'success'} />
              </span>
            </button>
            {openSessionId === session.id && (
              <div className="border-t border-white/10 px-4 py-3">
                {marksLoading && !marks ? (
                  <p className="text-sm text-white/45">Carregando…</p>
                ) : (
                  <ul className="flex flex-col gap-1.5">
                    {(marks ?? []).map((mark) => (
                      <li key={mark.enrollment_id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <span className="text-white/80">{studentNames[mark.enrollment_id] ?? 'Estudante'}</span>
                        <span className="flex items-center gap-2">
                          <StatusBadge
                            label={ATTENDANCE_MARK_LABELS[mark.status]}
                            tone={mark.status === 'presente' ? 'success' : mark.status === 'justificada' ? 'warning' : 'danger'}
                          />
                          {mark.note && <span className="text-xs text-white/40">{mark.note}</span>}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function AttendanceSummaryView({ classId }: { classId: string }) {
  const [summary, setSummary] = useState<AttendanceMonthlySummary[] | null>(null)
  const [studentNames, setStudentNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      getAttendanceSummary(classId, controller.signal),
      listEnrollments({ classId, page: 1, pageSize: 100, signal: controller.signal }),
    ])
      .then(([summaryPage, enrollmentPage]) => {
        setSummary(summaryPage.items)
        const byEnrollment = Object.fromEntries(enrollmentPage.items.map((item) => [item.id, item.student_id]))
        return getStudentNames(Object.values(byEnrollment), controller.signal).then((result) => ({
          names: result.names,
          byEnrollment,
        }))
      })
      .then(({ names, byEnrollment }) => {
        setStudentNames(
          Object.fromEntries(
            Object.entries(byEnrollment).map(([enrollmentId, studentId]) => [enrollmentId, names[studentId] ?? 'Estudante']),
          ),
        )
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [classId])

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-10 text-sm text-white/50">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        Carregando resumo…
      </div>
    )
  }

  if (error) return <p className="text-sm text-danger">{error}</p>

  if (!summary || summary.length === 0) {
    return (
      <EmptyState
        icon={ClipboardList}
        title="Ainda sem resumo mensal"
        description="Chamadas detalhadas viram resumo automaticamente depois de 6 meses. Até lá, consulte o histórico dia a dia."
      />
    )
  }

  return (
    <ul className="flex flex-col gap-2">
      {summary.map((row) => {
        const rate = row.total_sessions > 0 ? Math.round((row.present_count / row.total_sessions) * 100) : 0
        return (
          <li key={`${row.enrollment_id}-${row.period}`} className="liquid-glass flex flex-wrap items-center justify-between gap-3 border-l-2 border-l-brand-green/60 px-4 py-3">
            <div>
              <p className="text-sm text-white">{studentNames[row.enrollment_id] ?? 'Estudante'}</p>
              <p className="mt-1 text-xs text-white/45">
                {new Date(`${row.period}T00:00:00`).toLocaleDateString('pt-BR', { month: '2-digit', year: 'numeric' })}
                {' · '}{row.total_sessions} aula{row.total_sessions === 1 ? '' : 's'}
                {' · '}{row.absent_count} falta{row.absent_count === 1 ? '' : 's'}
                {row.justified_count > 0 && ` (${row.justified_count} justificada${row.justified_count === 1 ? '' : 's'})`}
              </p>
            </div>
            <span className="font-display text-sm text-brand-green">{rate}% presença</span>
          </li>
        )
      })}
    </ul>
  )
}
