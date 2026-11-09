import { ArrowUpRight, ClipboardList, Loader2, Search, UserPlus, UsersRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { useAuth } from '@/app/providers/AuthProvider'
import { getClassOccupancy, listClasses } from '@/features/classes/api'
import { changeEnrollmentStatus, createEnrollment, listEnrollments } from '@/features/enrollments/api'
import { getStudentNames, listStudents } from '@/features/students/api'
import type { SchoolClass } from '@/entities/class/types'
import { ENROLLMENT_STATUS_LABELS } from '@/entities/enrollment/types'
import type { Enrollment } from '@/entities/enrollment/types'
import type { Student } from '@/entities/student/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { OccupancyBar } from '@/shared/ui/OccupancyBar'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { EmptyState } from '@/shared/ui/EmptyState'
import { MetricCard } from '@/shared/ui/MetricCard'
import { PageFrame } from '@/shared/ui/PageFrame'
import { Select } from '@/shared/ui/Select'

/**
 * Matrícula é escopada por turma: a API não devolve nome de aluno nem de
 * turma dentro da matrícula (só IDs), então a tela parte da turma — que já
 * tem nome legível — e resolve o nome de cada aluno sob demanda.
 */
export function EnrollmentsPage() {
  usePageTitle('Matrículas')
  const { profile } = useAuth()
  const canCreateEnrollments = profile?.capabilities.includes('enrollments:create') ?? false
  const canManageEnrollments = profile?.capabilities.includes('enrollments:manage') ?? false

  const [classes, setClasses] = useState<SchoolClass[] | null>(null)
  const [selectedClassId, setSelectedClassId] = useState('')
  const selectedClass = classes?.find((item) => item.id === selectedClassId) ?? null

  const [enrollments, setEnrollments] = useState<Enrollment[] | null>(null)
  const [studentNames, setStudentNames] = useState<Record<string, string>>({})
  const [occupancy, setOccupancy] = useState<{ capacity: number; enrolled: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [showAddForm, setShowAddForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedSearch = useDebouncedValue(searchQuery)
  const [searchResults, setSearchResults] = useState<Student[]>([])
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  useEffect(() => {
    listClasses({ active: true, page: 1, pageSize: 100 })
      .then((result) => setClasses(result.items))
      .catch(() => setClasses([]))
  }, [])

  useEffect(() => {
    if (!selectedClassId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- limpa a seleção anterior ao trocar de turma
      setEnrollments(null)
      setOccupancy(null)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    Promise.all([
      listEnrollments({ classId: selectedClassId, page: 1, pageSize: 50, signal: controller.signal }),
      getClassOccupancy(selectedClassId, controller.signal),
    ])
      .then(([enrollmentPage, occ]) => {
        setEnrollments(enrollmentPage.items)
        setOccupancy({ capacity: occ.capacity, enrolled: occ.enrolled })
        getStudentNames(
          enrollmentPage.items.map((enrollment) => enrollment.student_id),
          controller.signal,
        )
          .then((result) => setStudentNames(result.names))
          .catch(() => {})
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [selectedClassId])

  useEffect(() => {
    if (!showAddForm || debouncedSearch.trim().length < 2) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- limpa resultados quando a busca fica curta demais
      setSearchResults([])
      return
    }
    const controller = new AbortController()
    listStudents({
      status: 'ativo',
      query: debouncedSearch.trim(),
      page: 1,
      pageSize: 10,
      signal: controller.signal,
    })
      .then((result) => setSearchResults(result.items))
      .catch(() => {})
    return () => controller.abort()
  }, [debouncedSearch, showAddForm])

  async function reloadEnrollments() {
    const [enrollmentPage, occ] = await Promise.all([
      listEnrollments({ classId: selectedClassId, page: 1, pageSize: 50 }),
      getClassOccupancy(selectedClassId),
    ])
    setEnrollments(enrollmentPage.items)
    setOccupancy({ capacity: occ.capacity, enrolled: occ.enrolled })
    const result = await getStudentNames(
      enrollmentPage.items.map((enrollment) => enrollment.student_id),
    ).catch(() => ({ names: {} as Record<string, string> }))
    setStudentNames(result.names)
  }

  async function handleAdd(studentId: string) {
    if (adding) return
    setAdding(true)
    setAddError(null)
    try {
      await createEnrollment(studentId, selectedClassId)
      setShowAddForm(false)
      setSearchQuery('')
      setSearchResults([])
      await reloadEnrollments()
    } catch (caught) {
      setAddError(friendlyMessage(caught))
    } finally {
      setAdding(false)
    }
  }

  const [changingEnrollmentId, setChangingEnrollmentId] = useState<string | null>(null)

  async function handleStatusChange(enrollment: Enrollment, reason: string) {
    const action = enrollment.status === 'ativa' ? 'cancel' : 'reactivate'
    try {
      await changeEnrollmentStatus(enrollment.id, action, {
        expected_updated_at: enrollment.updated_at,
        reason,
      })
      setChangingEnrollmentId(null)
      await reloadEnrollments()
    } catch (caught) {
      setError(friendlyMessage(caught))
    }
  }

  return (
    <PageFrame eyebrow="Vínculos e ocupação" title="Matrículas" description="Acompanhe quem está em cada turma, controle vagas e registre mudanças com histórico.">
      {selectedClassId && (
        <div className="grid gap-4 md:grid-cols-3"><MetricCard label="Turma selecionada" value={selectedClass?.name ?? '—'} icon={ClipboardList} /><MetricCard label="Vagas ocupadas" value={occupancy?.enrolled ?? '—'} icon={UsersRound} tone="blue" /><MetricCard label="Capacidade" value={occupancy?.capacity ?? '—'} icon={UsersRound} tone="amber" /></div>
      )}

      <div className={`liquid-glass border-t-2 border-t-brand-green/50 p-4 sm:p-5 ${selectedClassId ? 'mt-6' : ''}`}>
        <Select
          label="Turma"
          value={selectedClassId}
          onChange={(event) => setSelectedClassId(event.target.value)}
          disabled={!classes}
          options={[
            { value: '', label: classes ? 'Selecione uma turma' : 'Carregando turmas…' },
            ...(classes?.map((schoolClass) => ({ value: schoolClass.id, label: schoolClass.name })) ?? []),
          ]}
        />
      </div>

      {!selectedClassId && classes && classes.length === 0 && (
        <div className="mt-8"><EmptyState icon={ClipboardList} title="Nenhuma turma disponível" description="Crie uma turma antes de começar a registrar matrículas e acompanhar ocupação." action={<a href="/turmas/nova" className="inline-flex items-center gap-2 rounded-full bg-brand-green px-4 py-2.5 text-sm font-semibold text-ink">Criar turma <ArrowUpRight className="h-4 w-4" aria-hidden="true" /></a>} /></div>
      )}

      {selectedClassId && (
        <div className="mt-8 flex flex-col gap-6">
          {occupancy && selectedClass && (
            <div className="liquid-glass border-l-2 border-l-brand-green p-6">
              <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs uppercase tracking-[0.14em] text-white/40">Turma em foco</p><p className="mt-2 font-display text-lg font-semibold text-white">{selectedClass.name}</p></div><p className="text-xs text-white/45">{occupancy.enrolled} de {occupancy.capacity} vagas ocupadas</p></div>
              <div className="mt-5">
                <OccupancyBar capacity={occupancy.capacity} enrolled={occupancy.enrolled} />
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/35">Lista da turma</p><h2 className="mt-1 font-display text-xl font-semibold text-white">Estudantes matriculados</h2></div>
            {canCreateEnrollments && (
              <Button
                variant="secondary"
                onClick={() => setShowAddForm((value) => !value)}
                className="gap-2"
              >
                <UserPlus className="h-4 w-4" aria-hidden="true" />
                Nova matrícula
              </Button>
            )}
          </div>

          {showAddForm && canCreateEnrollments && (
            <div className="liquid-glass rounded-2xl p-5">
              <Input
                label="Buscar estudante"
                placeholder="Nome do estudante…"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                icon={<Search className="h-4 w-4" aria-hidden="true" />}
              />
              {addError && <p className="mt-2 text-sm text-danger">{addError}</p>}
              {searchResults.length > 0 && (
                <ul className="mt-3 flex flex-col gap-1">
                  {searchResults.map((student) => (
                    <li key={student.id}>
                      <button
                        type="button"
                        disabled={adding}
                        onClick={() => handleAdd(student.id)}
                        className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-white transition hover:bg-white/8 disabled:opacity-50"
                      >
                        {student.full_name}
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
              Carregando matrículas…
            </div>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}

          {!loading && !error && enrollments && enrollments.length === 0 && (
        <div className="liquid-glass flex flex-col items-center gap-3 border border-dashed border-white/15 p-10 text-center">
              <ClipboardList className="h-6 w-6 text-white/40" aria-hidden="true" />
              <p className="text-sm text-white/55">Esta turma ainda não possui estudantes.</p>
            </div>
          )}

          {!loading && !error && enrollments && enrollments.length > 0 && (
            <ul className="flex flex-col gap-2">
              {enrollments.map((enrollment, index) => (
                <li
                  key={enrollment.id}
                  className="liquid-glass flex flex-col gap-3 border-l-2 border-l-white/10 px-4 py-3 transition hover:border-l-brand-green"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="flex min-w-0 items-center gap-4"><span className="font-display text-xs text-white/30">{String(index + 1).padStart(2, '0')}</span><span className="break-words text-sm text-white">{studentNames[enrollment.student_id] ?? 'Carregando…'}</span></span>
                    <div className="flex items-center gap-3">
                      <StatusBadge
                        label={ENROLLMENT_STATUS_LABELS[enrollment.status]}
                        tone={enrollment.status === 'ativa' ? 'success' : 'neutral'}
                      />
                      {canManageEnrollments && (
                        <Button
                          type="button"
                          size="sm"
                          variant={enrollment.status === 'ativa' ? 'danger' : 'primary'}
                          onClick={() => setChangingEnrollmentId(enrollment.id)}
                        >
                          {enrollment.status === 'ativa' ? 'Cancelar' : 'Reativar'}
                        </Button>
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
              ))}
            </ul>
          )}
        </div>
      )}
    </PageFrame>
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
        label={isCancel ? 'Motivo do cancelamento' : 'Motivo da reativação'}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        disabled={submitting}
        hint="Pelo menos 10 caracteres."
      />
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" variant={isCancel ? 'danger' : 'primary'} loading={submitting}>
          {isCancel ? 'Confirmar cancelamento' : 'Confirmar reativação'}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}
