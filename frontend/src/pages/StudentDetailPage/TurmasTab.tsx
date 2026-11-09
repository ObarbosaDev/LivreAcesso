import { ClipboardList, Loader2, Search, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { getClass, listClasses } from '@/features/classes/api'
import { changeEnrollmentStatus, createEnrollment, listEnrollments } from '@/features/enrollments/api'
import type { SchoolClass } from '@/entities/class/types'
import { UNIT_LABELS, WEEKDAY_LABELS } from '@/entities/class/types'
import { ENROLLMENT_STATUS_LABELS } from '@/entities/enrollment/types'
import type { Enrollment } from '@/entities/enrollment/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { StatusBadge } from '@/shared/ui/StatusBadge'

export function TurmasTab({ studentId }: { studentId: string }) {
  const { profile } = useAuth()
  const canCreateEnrollments = profile?.capabilities.includes('enrollments:create') ?? false
  const canManageEnrollments = profile?.capabilities.includes('enrollments:manage') ?? false

  const [enrollments, setEnrollments] = useState<Enrollment[] | null>(null)
  const [classes, setClasses] = useState<Record<string, SchoolClass>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showAddForm, setShowAddForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedSearch = useDebouncedValue(searchQuery)
  const [searchResults, setSearchResults] = useState<SchoolClass[]>([])
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [changingEnrollmentId, setChangingEnrollmentId] = useState<string | null>(null)

  async function reload() {
    const page = await listEnrollments({ studentId, page: 1, pageSize: 50 })
    setEnrollments(page.items)
    const pairs = await Promise.all(
      page.items.map((enrollment) =>
        getClass(enrollment.class_id)
          .then((schoolClass) => [enrollment.class_id, schoolClass] as const)
          .catch(() => null),
      ),
    )
    setClasses(Object.fromEntries(pairs.filter((pair): pair is [string, SchoolClass] => pair !== null)))
  }

  useEffect(() => {
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)
    listEnrollments({ studentId, page: 1, pageSize: 50, signal: controller.signal })
      .then((page) => {
        setEnrollments(page.items)
        return Promise.all(
          page.items.map((enrollment) =>
            getClass(enrollment.class_id, controller.signal)
              .then((schoolClass) => [enrollment.class_id, schoolClass] as const)
              .catch(() => null),
          ),
        )
      })
      .then((pairs) => {
        if (!pairs) return
        setClasses(Object.fromEntries(pairs.filter((pair): pair is [string, SchoolClass] => pair !== null)))
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [studentId])

  useEffect(() => {
    if (!showAddForm || debouncedSearch.trim().length < 2) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- limpa resultados quando a busca fica curta demais
      setSearchResults([])
      return
    }
    const controller = new AbortController()
    listClasses({ active: true, query: debouncedSearch.trim(), page: 1, pageSize: 10, signal: controller.signal })
      .then((result) => setSearchResults(result.items))
      .catch(() => {})
    return () => controller.abort()
  }, [debouncedSearch, showAddForm])

  async function handleAdd(classId: string) {
    if (adding) return
    setAdding(true)
    setAddError(null)
    try {
      await createEnrollment(studentId, classId)
      setShowAddForm(false)
      setSearchQuery('')
      setSearchResults([])
      await reload()
    } catch (caught) {
      setAddError(friendlyMessage(caught))
    } finally {
      setAdding(false)
    }
  }

  async function handleStatusChange(enrollment: Enrollment, reason: string) {
    const action = enrollment.status === 'ativa' ? 'cancel' : 'reactivate'
    try {
      await changeEnrollmentStatus(enrollment.id, action, { expected_updated_at: enrollment.updated_at, reason })
      setChangingEnrollmentId(null)
      await reload()
    } catch (caught) {
      setError(friendlyMessage(caught))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/35">Programação</p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">Turmas matriculadas</h2>
        </div>
        {canCreateEnrollments && (
          <Button variant="secondary" onClick={() => setShowAddForm((value) => !value)} className="gap-2">
            <UserPlus className="h-4 w-4" aria-hidden="true" />
            Matricular em turma
          </Button>
        )}
      </div>

      {showAddForm && canCreateEnrollments && (
        <div className="liquid-glass rounded-2xl p-5">
          <Input
            label="Buscar turma"
            placeholder="Nome da turma…"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            icon={<Search className="h-4 w-4" aria-hidden="true" />}
          />
          {addError && <p className="mt-2 text-sm text-danger">{addError}</p>}
          {searchResults.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1">
              {searchResults.map((schoolClass) => (
                <li key={schoolClass.id}>
                  <button
                    type="button"
                    disabled={adding}
                    onClick={() => handleAdd(schoolClass.id)}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-white transition hover:bg-white/8 disabled:opacity-50"
                  >
                    <span>
                      {schoolClass.name}
                      <span className="ml-2 text-xs text-white/40">{UNIT_LABELS[schoolClass.unit]}</span>
                    </span>
                    <span className="text-xs text-white/40">Matricular</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center gap-2 py-12 text-sm text-white/50">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Carregando turmas…
        </div>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {!loading && !error && enrollments && enrollments.length === 0 && (
        <div className="liquid-glass flex flex-col items-center gap-3 border border-dashed border-white/15 p-10 text-center">
          <ClipboardList className="h-6 w-6 text-white/40" aria-hidden="true" />
          <p className="text-sm text-white/55">Este estudante ainda não está matriculado em nenhuma turma.</p>
        </div>
      )}

      {!loading && !error && enrollments && enrollments.length > 0 && (
        <ul className="flex flex-col gap-2">
          {enrollments.map((enrollment, index) => {
            const schoolClass = classes[enrollment.class_id]
            return (
              <li
                key={enrollment.id}
                className="liquid-glass flex flex-col gap-3 border-l-2 border-l-white/10 px-4 py-3 transition hover:border-l-brand-green"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-4">
                    <span className="font-display text-xs text-white/30">{String(index + 1).padStart(2, '0')}</span>
                    <span className="flex flex-col">
                      {schoolClass ? (
                        <Link to={`/turmas/${schoolClass.id}`} className="text-sm text-white hover:text-brand-green">
                          {schoolClass.name}
                        </Link>
                      ) : (
                        <span className="text-sm text-white/50">Carregando…</span>
                      )}
                      {schoolClass && (
                        <span className="text-xs text-white/40">
                          {UNIT_LABELS[schoolClass.unit]}
                          {schoolClass.schedules[0] && (
                            <>
                              {' · '}
                              {WEEKDAY_LABELS[schoolClass.schedules[0].weekday]}{' '}
                              {schoolClass.schedules[0].starts_at.slice(0, 5)}
                            </>
                          )}
                        </span>
                      )}
                    </span>
                  </span>
                  <div className="flex items-center gap-3">
                    <StatusBadge
                      label={ENROLLMENT_STATUS_LABELS[enrollment.status]}
                      tone={enrollment.status === 'ativa' ? 'success' : 'neutral'}
                    />
                    {canManageEnrollments && (
                      <button
                        type="button"
                        onClick={() => setChangingEnrollmentId(enrollment.id)}
                        className={
                          enrollment.status === 'ativa'
                            ? 'text-xs font-medium text-danger/80 hover:text-danger'
                            : 'text-xs font-medium text-brand-green hover:text-brand-green-soft'
                        }
                      >
                        {enrollment.status === 'ativa' ? 'Remover' : 'Reativar'}
                      </button>
                    )}
                  </div>
                </div>
                {changingEnrollmentId === enrollment.id && (
                  <EnrollmentStatusForm
                    enrollment={enrollment}
                    onCancel={() => setChangingEnrollmentId(null)}
                    onConfirm={(reason) => handleStatusChange(enrollment, reason)}
                  />
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function EnrollmentStatusForm({
  enrollment,
  onCancel,
  onConfirm,
}: {
  enrollment: Enrollment
  onCancel: () => void
  onConfirm: (reason: string) => Promise<void>
}) {
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isCancel = enrollment.status === 'ativa'

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (reason.trim().length < 10) {
      setError('Informe um motivo com pelo menos 10 caracteres.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await onConfirm(reason)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 border-t border-white/10 pt-3">
      <Input
        label={isCancel ? 'Motivo da remoção' : 'Motivo da reativação'}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        disabled={submitting}
        hint="Pelo menos 10 caracteres."
      />
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" variant={isCancel ? 'danger' : 'primary'} loading={submitting}>
          {isCancel ? 'Confirmar remoção' : 'Confirmar reativação'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}
