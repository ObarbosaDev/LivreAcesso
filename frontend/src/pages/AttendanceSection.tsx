import {
  AlertCircle,
  CalendarCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  History,
  Loader2,
  Table2,
  Users,
  XCircle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

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
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/Button'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Input } from '@/shared/ui/Input'
import { StatusBadge } from '@/shared/ui/StatusBadge'

type View = 'chamada' | 'historico' | 'resumo' | 'diario'

const TABS: { value: View; label: string; icon: LucideIcon }[] = [
  { value: 'chamada', label: 'Tirar chamada', icon: CalendarCheck },
  { value: 'diario', label: 'Diário', icon: Table2 },
  { value: 'historico', label: 'Histórico', icon: History },
  { value: 'resumo', label: 'Resumo mensal', icon: ClipboardList },
]

const JOURNAL_CELL_LABEL: Record<AttendanceMarkStatus, string> = { presente: 'P', ausente: 'F', justificada: 'J' }

const JOURNAL_CELL_TONE: Record<AttendanceMarkStatus, string> = {
  presente: 'border-brand-green/40 bg-brand-green/15 text-brand-green',
  ausente: 'border-danger/40 bg-danger/15 text-danger',
  justificada: 'border-warning/40 bg-warning/15 text-warning',
}

const MARK_TONE: Record<AttendanceMarkStatus, string> = {
  presente: 'border-brand-green bg-brand-green text-ink',
  ausente: 'border-danger bg-danger text-ink',
  justificada: 'border-warning bg-warning text-ink',
}

const MARK_ROW_BORDER: Record<AttendanceMarkStatus | '', string> = {
  presente: 'border-l-brand-green',
  ausente: 'border-l-danger',
  justificada: 'border-l-warning',
  '': 'border-l-white/10',
}

const MARK_OPTIONS: { value: AttendanceMarkStatus; icon: LucideIcon }[] = [
  { value: 'presente', icon: CheckCircle2 },
  { value: 'ausente', icon: XCircle },
  { value: 'justificada', icon: AlertCircle },
]

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

const WEEKDAY_LABELS_SHORT = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

function buildMonthCells(year: number, month: number): (string | null)[] {
  const firstWeekday = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (string | null)[] = Array.from({ length: firstWeekday }, () => null)
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(`${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`)
  }
  return cells
}

function formatWeekdayDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('pt-BR', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function formatMonthYear(iso: string) {
  const label = new Date(`${iso}T00:00:00`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
  return label.charAt(0).toUpperCase() + label.slice(1)
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
      {showHeader && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/35">Frequência</p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">Chamada</h2>
          <p className="mt-1 text-xs text-white/45">
            Chamadas ficam detalhadas por até 6 meses; depois disso viram um resumo mensal por estudante.
          </p>
        </div>
      )}

      <div className="flex gap-1 overflow-x-auto border-b border-white/10">
        {TABS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => setView(value)}
            className={cn(
              'flex shrink-0 items-center gap-2 px-4 py-2.5 text-sm font-medium transition',
              view === value ? 'border-b-2 border-brand-green text-white' : 'text-white/50 hover:text-white',
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      {view === 'chamada' && <TakeAttendance classId={classId} canTakeAttendance={canTakeAttendance} />}
      {view === 'diario' && <AttendanceJournal classId={classId} />}
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
  const [sessionsByDate, setSessionsByDate] = useState<Record<string, AttendanceSessionSummary> | null>(null)
  const [viewDate, setViewDate] = useState(() => new Date(`${todayISO()}T00:00:00`))
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
    setSessionsByDate(null)
    listAttendanceSessions(classId, 100, 0, controller.signal)
      .then((page) => {
        setSessionsByDate(Object.fromEntries(page.items.map((item) => [item.session_date, item])))
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
    return () => controller.abort()
  }, [classId])

  useEffect(() => {
    if (sessionsByDate === null) return
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)
    setSaved(false)
    const existing = sessionsByDate[date] ?? null
    if (!existing) {
      setSessionId(null)
      setDrafts({})
      setLoading(false)
      return
    }
    setSessionId(existing.id)
    getAttendanceSessionMarks(existing.id, controller.signal)
      .then((marks) => {
        setDrafts(
          Object.fromEntries(
            marks.map((mark) => [mark.enrollment_id, { status: mark.status, note: mark.note ?? '' }]),
          ),
        )
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [date, sessionsByDate])

  function setDraft(enrollmentId: string, patch: Partial<MarkDraft>) {
    setDrafts((current) => ({
      ...current,
      [enrollmentId]: { status: current[enrollmentId]?.status ?? '', note: current[enrollmentId]?.note ?? '', ...patch },
    }))
  }

  function markAllPresent() {
    setDrafts((current) => {
      const next = { ...current }
      for (const enrollment of enrollments) {
        if (!next[enrollment.id]?.status) next[enrollment.id] = { status: 'presente', note: '' }
      }
      return next
    })
  }

  const tally = useMemo(() => {
    const counts = { presente: 0, ausente: 0, justificada: 0 }
    for (const enrollment of enrollments) {
      const status = drafts[enrollment.id]?.status
      if (status) counts[status] += 1
    }
    const marked = counts.presente + counts.ausente + counts.justificada
    return { ...counts, marked, unmarked: enrollments.length - marked }
  }, [enrollments, drafts])

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
      let openSession: AttendanceSessionSummary | null = sessionId ? sessionsByDate?.[date] ?? null : null
      if (!openSession) {
        openSession = await openAttendanceSession(classId, date)
        setSessionId(openSession.id)
      }
      const activeSession = openSession
      await recordAttendanceMarks(
        activeSession.id,
        enrollments.map((enrollment) => ({
          enrollment_id: enrollment.id,
          status: drafts[enrollment.id].status as AttendanceMarkStatus,
          note: drafts[enrollment.id].status === 'justificada' ? drafts[enrollment.id].note.trim() : undefined,
        })),
      )
      setSessionsByDate((current) => ({ ...(current ?? {}), [date]: activeSession }))
      setSaved(true)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  function goToToday() {
    setDate(todayISO())
    setViewDate(new Date(`${todayISO()}T00:00:00`))
  }

  function shiftMonth(delta: number) {
    setViewDate((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1))
  }

  const calendarCells = useMemo(() => buildMonthCells(viewDate.getFullYear(), viewDate.getMonth()), [viewDate])
  const isViewingCurrentMonth =
    viewDate.getFullYear() === Number(todayISO().slice(0, 4)) && viewDate.getMonth() === Number(todayISO().slice(5, 7)) - 1

  return (
    <div className="flex flex-col gap-4">
      <div className="liquid-glass flex flex-col gap-5 border-t-2 border-t-brand-green/50 p-4 sm:p-5 lg:flex-row lg:items-start lg:gap-8">
        <div className="w-full lg:max-w-[18rem]">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => shiftMonth(-1)}
              className="flex h-8 w-8 items-center justify-center border border-white/15 text-white/55 transition hover:border-brand-green hover:text-brand-green"
              aria-label="Mês anterior"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </button>
            <p className="font-display text-sm font-semibold text-white">
              {formatMonthYear(`${viewDate.getFullYear()}-${String(viewDate.getMonth() + 1).padStart(2, '0')}-01`)}
            </p>
            <button
              type="button"
              onClick={() => !isViewingCurrentMonth && shiftMonth(1)}
              disabled={isViewingCurrentMonth}
              className="flex h-8 w-8 items-center justify-center border border-white/15 text-white/55 transition hover:border-brand-green hover:text-brand-green disabled:pointer-events-none disabled:opacity-30"
              aria-label="Próximo mês"
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>

          <div className="mt-3 grid grid-cols-7 gap-1 text-center text-[10px] uppercase tracking-wide text-white/35">
            {WEEKDAY_LABELS_SHORT.map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {calendarCells.map((iso, index) => {
              if (!iso) return <div key={`empty-${index}`} aria-hidden="true" />
              const isFuture = iso > todayISO()
              const isSelected = iso === date
              const isToday = iso === todayISO()
              const hasSession = Boolean(sessionsByDate?.[iso])
              return (
                <button
                  key={iso}
                  type="button"
                  disabled={isFuture}
                  onClick={() => setDate(iso)}
                  className={cn(
                    'relative flex aspect-square items-center justify-center border text-xs transition disabled:cursor-not-allowed disabled:border-transparent disabled:text-white/15',
                    isSelected
                      ? 'border-brand-green bg-brand-green font-semibold text-ink'
                      : isToday
                        ? 'border-brand-green/50 text-brand-green hover:bg-white/5'
                        : 'border-white/10 text-white/70 hover:border-brand-green/50 hover:text-white',
                  )}
                >
                  {Number(iso.slice(8, 10))}
                  {hasSession && !isSelected && (
                    <span className="absolute bottom-1 h-1 w-1 rounded-full bg-brand-green" aria-hidden="true" />
                  )}
                </button>
              )
            })}
          </div>

          {date !== todayISO() && (
            <button type="button" onClick={goToToday} className="mt-3 text-xs font-medium text-brand-green hover:text-brand-green-soft">
              Voltar para hoje
            </button>
          )}
        </div>

        <div className="flex flex-1 flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-white/35">Data selecionada</p>
              <p className="mt-1 font-display text-lg font-semibold capitalize text-white">{formatWeekdayDate(date)}</p>
            </div>
            {sessionId && <StatusBadge label="Chamada já registrada nesta data" tone="success" />}
          </div>

          {!loading && enrollments.length > 0 && (
            <div className="flex flex-wrap items-center gap-4 border-t border-white/10 pt-4 text-xs">
              <TallyChip icon={CheckCircle2} label="Presentes" value={tally.presente} className="text-brand-green" />
              <TallyChip icon={XCircle} label="Faltas" value={tally.ausente} className="text-danger" />
              <TallyChip icon={AlertCircle} label="Justificadas" value={tally.justificada} className="text-warning" />
              {tally.unmarked > 0 && (
                <TallyChip icon={Users} label="Faltam marcar" value={tally.unmarked} className="text-white/45" />
              )}
              {canTakeAttendance && tally.unmarked > 0 && (
                <button
                  type="button"
                  onClick={markAllPresent}
                  className="ml-auto text-xs font-medium text-brand-green hover:text-brand-green-soft"
                >
                  Marcar todos presentes
                </button>
              )}
            </div>
          )}
        </div>
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
              <div
                key={enrollment.id}
                className={cn(
                  'liquid-glass flex flex-col gap-3 border-l-2 px-4 py-3 transition',
                  MARK_ROW_BORDER[draft.status],
                )}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-4">
                    <span className="font-display text-xs text-white/30">{String(index + 1).padStart(2, '0')}</span>
                    <span className="text-sm text-white">{studentNames[enrollment.student_id] ?? 'Carregando…'}</span>
                  </span>
                  <div className="flex gap-1.5">
                    {MARK_OPTIONS.map((option) => {
                      const selected = draft.status === option.value
                      return (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => setDraft(enrollment.id, { status: option.value })}
                          className={cn(
                            'inline-flex h-8 items-center gap-1.5 border px-2.5 text-xs font-medium transition disabled:pointer-events-none',
                            selected ? MARK_TONE[option.value] : 'border-white/15 bg-white/5 text-white/55 hover:border-white/30 hover:text-white',
                          )}
                        >
                          <option.icon className="h-3.5 w-3.5" aria-hidden="true" />
                          {ATTENDANCE_MARK_LABELS[option.value]}
                        </button>
                      )
                    })}
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

function TallyChip({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon: LucideIcon
  label: string
  value: number
  className?: string
}) {
  return (
    <span className={cn('flex items-center gap-1.5', className)}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      <span className="font-display font-semibold">{value}</span>
      <span className="text-white/45">{label}</span>
    </span>
  )
}

function AttendanceJournal({ classId }: { classId: string }) {
  const [viewDate, setViewDate] = useState(() => new Date(`${todayISO()}T00:00:00`))
  const [enrollments, setEnrollments] = useState<Enrollment[]>([])
  const [studentNames, setStudentNames] = useState<Record<string, string>>({})
  const [sessions, setSessions] = useState<AttendanceSessionSummary[]>([])
  const [marksBySession, setMarksBySession] = useState<Record<string, AttendanceMark[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const monthPrefix = `${viewDate.getFullYear()}-${String(viewDate.getMonth() + 1).padStart(2, '0')}`

  useEffect(() => {
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)
    Promise.all([
      listEnrollments({ classId, status: 'ativa', page: 1, pageSize: 100, signal: controller.signal }),
      listAttendanceSessions(classId, 100, 0, controller.signal),
    ])
      .then(async ([enrollmentPage, sessionPage]) => {
        setEnrollments(enrollmentPage.items)
        const names = await getStudentNames(enrollmentPage.items.map((item) => item.student_id), controller.signal)
        setStudentNames(names.names)

        const monthSessions = sessionPage.items
          .filter((session) => session.session_date.startsWith(monthPrefix))
          .sort((a, b) => (a.session_date < b.session_date ? -1 : 1))
        setSessions(monthSessions)

        const marksEntries = await Promise.all(
          monthSessions.map((session) =>
            getAttendanceSessionMarks(session.id, controller.signal).then((marks) => [session.id, marks] as const),
          ),
        )
        setMarksBySession(Object.fromEntries(marksEntries))
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [classId, monthPrefix])

  function shiftMonth(delta: number) {
    setViewDate((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1))
  }

  const isViewingCurrentMonth =
    viewDate.getFullYear() === Number(todayISO().slice(0, 4)) && viewDate.getMonth() === Number(todayISO().slice(5, 7)) - 1

  const totals = useMemo(() => {
    const map: Record<string, { present: number; total: number }> = {}
    for (const enrollment of enrollments) {
      let present = 0
      let total = 0
      for (const session of sessions) {
        const mark = marksBySession[session.id]?.find((item) => item.enrollment_id === enrollment.id)
        if (mark) {
          total += 1
          if (mark.status === 'presente') present += 1
        }
      }
      map[enrollment.id] = { present, total }
    }
    return map
  }, [enrollments, sessions, marksBySession])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => shiftMonth(-1)}
          className="flex h-8 w-8 items-center justify-center border border-white/15 text-white/55 transition hover:border-brand-green hover:text-brand-green"
          aria-label="Mês anterior"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </button>
        <p className="font-display text-sm font-semibold text-white">{formatMonthYear(`${monthPrefix}-01`)}</p>
        <button
          type="button"
          onClick={() => !isViewingCurrentMonth && shiftMonth(1)}
          disabled={isViewingCurrentMonth}
          className="flex h-8 w-8 items-center justify-center border border-white/15 text-white/55 transition hover:border-brand-green hover:text-brand-green disabled:pointer-events-none disabled:opacity-30"
          aria-label="Próximo mês"
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-10 text-sm text-white/50">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Carregando diário…
        </div>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {!loading && !error && enrollments.length === 0 && (
        <EmptyState icon={Table2} title="Sem estudantes ativos" description="Matricule estudantes nesta turma para ver o diário." />
      )}

      {!loading && !error && enrollments.length > 0 && sessions.length === 0 && (
        <EmptyState icon={Table2} title="Nenhuma chamada neste mês" description="O diário mostra os dias em que a chamada foi tirada neste mês." />
      )}

      {!loading && !error && enrollments.length > 0 && sessions.length > 0 && (
        <div className="liquid-glass overflow-x-auto p-2">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="sticky left-0 z-10 whitespace-nowrap bg-surface px-3 py-2 text-left font-medium text-white/45">
                  Estudante
                </th>
                {sessions.map((session) => (
                  <th key={session.id} className="px-1 py-2 text-center font-medium text-white/45">
                    {Number(session.session_date.slice(8, 10))}
                  </th>
                ))}
                <th className="whitespace-nowrap px-3 py-2 text-right font-medium text-white/45">Presença</th>
              </tr>
            </thead>
            <tbody>
              {enrollments.map((enrollment) => {
                const total = totals[enrollment.id]
                const rate = total && total.total > 0 ? Math.round((total.present / total.total) * 100) : null
                return (
                  <tr key={enrollment.id} className="border-t border-white/8">
                    <td className="sticky left-0 z-10 whitespace-nowrap bg-surface px-3 py-2 text-white">
                      {studentNames[enrollment.student_id] ?? 'Carregando…'}
                    </td>
                    {sessions.map((session) => {
                      const mark = marksBySession[session.id]?.find((item) => item.enrollment_id === enrollment.id)
                      return (
                        <td key={session.id} className="px-1 py-2 text-center">
                          <span
                            className={cn(
                              'mx-auto flex h-6 w-6 items-center justify-center border text-[10px] font-semibold',
                              mark ? JOURNAL_CELL_TONE[mark.status] : 'border-white/10 text-white/20',
                            )}
                          >
                            {mark ? JOURNAL_CELL_LABEL[mark.status] : '–'}
                          </span>
                        </td>
                      )
                    })}
                    <td className="whitespace-nowrap px-3 py-2 text-right font-display text-white">
                      {rate !== null ? `${rate}%` : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
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
        const total = marks?.length ?? 0
        const presentCount = marks?.filter((mark) => mark.status === 'presente').length ?? 0
        const absentCount = marks?.filter((mark) => mark.status === 'ausente').length ?? 0
        const justifiedCount = marks?.filter((mark) => mark.status === 'justificada').length ?? 0
        return (
          <li key={session.id} className="liquid-glass border-l-2 border-l-white/10 transition hover:border-l-brand-green">
            <button
              type="button"
              onClick={() => void toggleSession(session.id)}
              className="flex w-full flex-col gap-2 px-4 py-3 text-left"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="flex items-center gap-2.5 text-sm text-white">
                  <CalendarCheck className="h-4 w-4 text-white/30" aria-hidden="true" />
                  {formatWeekdayDate(session.session_date)}
                </span>
                <span className="flex items-center gap-3">
                  {marks && <span className="text-xs text-white/45">{presentCount}/{total} presentes</span>}
                  <StatusBadge label={session.status === 'fechada' ? 'Fechada' : 'Editável'} tone={session.status === 'fechada' ? 'neutral' : 'success'} />
                </span>
              </div>
              {marks && total > 0 && (
                <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-white/8">
                  <div className="h-full bg-brand-green" style={{ width: `${(presentCount / total) * 100}%` }} />
                  <div className="h-full bg-warning" style={{ width: `${(justifiedCount / total) * 100}%` }} />
                  <div className="h-full bg-danger" style={{ width: `${(absentCount / total) * 100}%` }} />
                </div>
              )}
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

  const groupedByPeriod = useMemo(() => {
    if (!summary) return []
    const groups = new Map<string, AttendanceMonthlySummary[]>()
    for (const row of summary) {
      const bucket = groups.get(row.period) ?? []
      bucket.push(row)
      groups.set(row.period, bucket)
    }
    return Array.from(groups.entries()).sort(([a], [b]) => (a < b ? 1 : -1))
  }, [summary])

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
    <div className="flex flex-col gap-6">
      {groupedByPeriod.map(([period, rows]) => (
        <section key={period} className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-green">{formatMonthYear(period)}</p>
          <ul className="flex flex-col gap-2">
            {rows.map((row) => {
              const rate = row.total_sessions > 0 ? Math.round((row.present_count / row.total_sessions) * 100) : 0
              const tone = rate >= 85 ? 'bg-brand-green' : rate >= 60 ? 'bg-warning' : 'bg-danger'
              const rateColor = rate >= 85 ? 'text-brand-green' : rate >= 60 ? 'text-warning' : 'text-danger'
              return (
                <li key={`${row.enrollment_id}-${row.period}`} className="liquid-glass flex flex-col gap-3 border-l-2 border-l-white/10 px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-white">{studentNames[row.enrollment_id] ?? 'Estudante'}</p>
                    <span className={cn('font-display text-sm font-semibold', rateColor)}>{rate}% presença</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/8">
                    <div className={cn('h-full rounded-full', tone)} style={{ width: `${Math.min(rate, 100)}%` }} />
                  </div>
                  <p className="text-xs text-white/45">
                    {row.total_sessions} aula{row.total_sessions === 1 ? '' : 's'}
                    {' · '}{row.absent_count} falta{row.absent_count === 1 ? '' : 's'}
                    {row.justified_count > 0 && ` (${row.justified_count} justificada${row.justified_count === 1 ? '' : 's'})`}
                  </p>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}
