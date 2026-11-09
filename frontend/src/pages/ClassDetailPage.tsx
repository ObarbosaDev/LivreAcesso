import { ArrowLeft, ClipboardList, Download, Loader2, Search, UserPlus } from 'lucide-react'
import autoTable from 'jspdf-autotable'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import {
  activateClass,
  deactivateClass,
  getClass,
  getClassOccupancy,
  listModalities,
  updateClass,
} from '@/features/classes/api'
import { changeEnrollmentStatus, createEnrollment, listEnrollments } from '@/features/enrollments/api'
import { listProfiles } from '@/features/profiles/api'
import { getStudentNames, listStudents } from '@/features/students/api'
import type { Modality, SchoolClass, Unit, Weekday } from '@/entities/class/types'
import { UNIT_LABELS, UNITS, WEEKDAYS, WEEKDAY_LABELS } from '@/entities/class/types'
import { ENROLLMENT_STATUS_LABELS } from '@/entities/enrollment/types'
import type { Enrollment } from '@/entities/enrollment/types'
import type { Profile } from '@/entities/profile/types'
import type { Student } from '@/entities/student/types'
import { AttendanceSection } from '@/pages/AttendanceSection'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { addPdfFooter, createBrandedPdf, PDF_TABLE_THEME } from '@/shared/lib/pdf'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { MetricCard } from '@/shared/ui/MetricCard'
import { OccupancyBar } from '@/shared/ui/OccupancyBar'
import { PageFrame } from '@/shared/ui/PageFrame'
import { Select } from '@/shared/ui/Select'
import { StatusBadge } from '@/shared/ui/StatusBadge'

export function ClassDetailPage() {
  const { classId } = useParams<{ classId: string }>()
  const { profile } = useAuth()
  const canManageClasses = profile?.capabilities.includes('classes:manage') ?? false
  const canCreateEnrollments = profile?.capabilities.includes('enrollments:create') ?? false
  const canManageEnrollments = profile?.capabilities.includes('enrollments:manage') ?? false
  const canTakeAttendance = profile?.capabilities.includes('attendance:manage') ?? false

  usePageTitle('Turma')

  const [schoolClass, setSchoolClass] = useState<SchoolClass | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!classId) return
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)
    getClass(classId, controller.signal)
      .then(setSchoolClass)
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [classId])

  if (!classId) return null

  return (
    <PageFrame
      eyebrow="Programação e capacidade"
      title={schoolClass?.name ?? 'Turma'}
      description="Edite os dados da turma e gerencie quem está matriculado."
    >
      <Link
        to="/turmas"
        className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-white/50 transition hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Voltar para turmas
      </Link>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-white/50">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Carregando turma…
        </div>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {!loading && !error && schoolClass && (
        <div className="flex flex-col gap-8">
          <ClassEditForm
            schoolClass={schoolClass}
            canManageClasses={canManageClasses}
            onUpdated={setSchoolClass}
          />
          <ClassRoster
            classId={classId}
            className={schoolClass.name}
            canCreateEnrollments={canCreateEnrollments}
            canManageEnrollments={canManageEnrollments}
          />
          <AttendanceSection classId={classId} canTakeAttendance={canTakeAttendance} />
        </div>
      )}
    </PageFrame>
  )
}

function ClassEditForm({
  schoolClass,
  canManageClasses,
  onUpdated,
}: {
  schoolClass: SchoolClass
  canManageClasses: boolean
  onUpdated: (schoolClass: SchoolClass) => void
}) {
  const [modalities, setModalities] = useState<Modality[]>([])
  const [instructors, setInstructors] = useState<Profile[]>([])

  const [modalityId, setModalityId] = useState(schoolClass.modality_id)
  const [unit, setUnit] = useState<Unit>(schoolClass.unit)
  const [name, setName] = useState(schoolClass.name)
  const [capacity, setCapacity] = useState(String(schoolClass.capacity))
  const [location, setLocation] = useState(schoolClass.location)
  const [minimumAge, setMinimumAge] = useState(schoolClass.minimum_age?.toString() ?? '')
  const [maximumAge, setMaximumAge] = useState(schoolClass.maximum_age?.toString() ?? '')
  const [weekday, setWeekday] = useState<Weekday>(schoolClass.schedules[0]?.weekday ?? 'segunda')
  const [startsAt, setStartsAt] = useState(schoolClass.schedules[0]?.starts_at.slice(0, 5) ?? '09:00')
  const [endsAt, setEndsAt] = useState(schoolClass.schedules[0]?.ends_at.slice(0, 5) ?? '10:00')
  const [selectedInstructors, setSelectedInstructors] = useState<string[]>(
    schoolClass.instructors.map((instructor) => instructor.id),
  )

  const [submitting, setSubmitting] = useState(false)
  const [activationBusy, setActivationBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listModalities(true).then((result) => setModalities(result.items)).catch(() => {})
    listProfiles({ role: 'instrutor', active: true, page: 1, pageSize: 100 })
      .then((result) => setInstructors(result.items))
      .catch(() => {})
  }, [])

  function toggleInstructor(id: string) {
    setSelectedInstructors((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setError(null)

    if (selectedInstructors.length === 0) {
      setError('Selecione ao menos um instrutor.')
      return
    }

    setSubmitting(true)
    try {
      const updated = await updateClass(schoolClass.id, {
        modality_id: modalityId,
        unit,
        name,
        capacity: Number(capacity),
        location,
        minimum_age: minimumAge ? Number(minimumAge) : undefined,
        maximum_age: maximumAge ? Number(maximumAge) : undefined,
        schedules: [{ weekday, starts_at: startsAt, ends_at: endsAt }],
        instructor_ids: selectedInstructors,
        expected_updated_at: schoolClass.updated_at,
      })
      onUpdated(updated)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleToggleActive() {
    const reason = schoolClass.active
      ? 'Turma desativada pela coordenação.'
      : 'Turma reativada pela coordenação.'
    setActivationBusy(true)
    setError(null)
    try {
      const updated = schoolClass.active
        ? await deactivateClass(schoolClass.id, schoolClass.updated_at, reason)
        : await activateClass(schoolClass.id, schoolClass.updated_at, reason)
      onUpdated(updated)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setActivationBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col items-start gap-6">
      <div className="flex w-full flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/35">Dados da turma</p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">Editar</h2>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge label={schoolClass.active ? 'Ativa' : 'Inativa'} tone={schoolClass.active ? 'success' : 'neutral'} />
          {canManageClasses && (
            <Button
              type="button"
              variant={schoolClass.active ? 'danger' : 'secondary'}
              onClick={() => void handleToggleActive()}
              loading={activationBusy}
            >
              {schoolClass.active ? 'Desativar turma' : 'Reativar turma'}
            </Button>
          )}
        </div>
      </div>

      <fieldset
        disabled={!canManageClasses || submitting}
        className="liquid-glass flex w-full flex-col gap-5 rounded-2xl p-6 disabled:opacity-60"
      >
        <legend className="px-1 font-display text-sm font-semibold text-white">Modalidade e unidade</legend>
        <Select
          label="Modalidade"
          value={modalityId}
          onChange={(event) => setModalityId(event.target.value)}
          options={modalities.map((modality) => ({ value: modality.id, label: modality.name }))}
        />
        <Select
          label="Unidade"
          value={unit}
          onChange={(event) => setUnit(event.target.value as Unit)}
          options={UNITS.map((value) => ({ value, label: UNIT_LABELS[value] }))}
        />
        <Input label="Nome da turma" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Capacidade"
            type="number"
            min={1}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
          />
          <Input label="Local" value={location} onChange={(e) => setLocation(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Idade mínima (opcional)"
            type="number"
            value={minimumAge}
            onChange={(e) => setMinimumAge(e.target.value)}
          />
          <Input
            label="Idade máxima (opcional)"
            type="number"
            value={maximumAge}
            onChange={(e) => setMaximumAge(e.target.value)}
          />
        </div>
      </fieldset>

      <fieldset
        disabled={!canManageClasses || submitting}
        className="liquid-glass flex w-full flex-col gap-4 rounded-2xl p-6 disabled:opacity-60"
      >
        <legend className="px-1 font-display text-sm font-semibold text-white">Horário</legend>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Select
            label="Dia"
            value={weekday}
            onChange={(event) => setWeekday(event.target.value as Weekday)}
            options={WEEKDAYS.map((value) => ({ value, label: WEEKDAY_LABELS[value] }))}
          />
          <Input label="Início" type="time" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} />
          <Input label="Fim" type="time" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
        </div>
      </fieldset>

      <fieldset
        disabled={!canManageClasses || submitting}
        className="liquid-glass flex w-full flex-col gap-3 rounded-2xl p-6 disabled:opacity-60"
      >
        <legend className="px-1 font-display text-sm font-semibold text-white">Instrutores</legend>
        {instructors.length === 0 && (
          <p className="text-sm text-white/50">Nenhum instrutor ativo cadastrado na equipe ainda.</p>
        )}
        <div className="flex flex-col gap-2">
          {instructors.map((instructor) => (
            <label key={instructor.id} className="flex items-center gap-2.5 text-sm text-white">
              <input
                type="checkbox"
                checked={selectedInstructors.includes(instructor.id)}
                onChange={() => toggleInstructor(instructor.id)}
                className="h-4 w-4 rounded border-white/20 bg-white/5 accent-brand-green"
              />
              {instructor.full_name}
            </label>
          ))}
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      {canManageClasses && (
        <Button type="submit" loading={submitting}>
          {submitting ? 'Salvando…' : 'Salvar alterações'}
        </Button>
      )}
    </form>
  )
}

function ClassRoster({
  classId,
  className,
  canCreateEnrollments,
  canManageEnrollments,
}: {
  classId: string
  className: string
  canCreateEnrollments: boolean
  canManageEnrollments: boolean
}) {
  const [enrollments, setEnrollments] = useState<Enrollment[] | null>(null)
  const [studentNames, setStudentNames] = useState<Record<string, string>>({})
  const [occupancy, setOccupancy] = useState<{ capacity: number; enrolled: number } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showAddForm, setShowAddForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedSearch = useDebouncedValue(searchQuery)
  const [searchResults, setSearchResults] = useState<Student[]>([])
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)
  const [changingEnrollmentId, setChangingEnrollmentId] = useState<string | null>(null)

  async function reload() {
    const [enrollmentPage, occ] = await Promise.all([
      listEnrollments({ classId, page: 1, pageSize: 50 }),
      getClassOccupancy(classId),
    ])
    setEnrollments(enrollmentPage.items)
    setOccupancy({ capacity: occ.capacity, enrolled: occ.enrolled })
    const result = await getStudentNames(enrollmentPage.items.map((enrollment) => enrollment.student_id)).catch(
      () => ({ names: {} as Record<string, string> }),
    )
    setStudentNames(result.names)
  }

  useEffect(() => {
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)
    Promise.all([
      listEnrollments({ classId, page: 1, pageSize: 50, signal: controller.signal }),
      getClassOccupancy(classId, controller.signal),
    ])
      .then(([enrollmentPage, occ]) => {
        setEnrollments(enrollmentPage.items)
        setOccupancy({ capacity: occ.capacity, enrolled: occ.enrolled })
        getStudentNames(enrollmentPage.items.map((enrollment) => enrollment.student_id), controller.signal)
          .then((result) => setStudentNames(result.names))
          .catch(() => {})
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught))
      })
      .finally(() => setLoading(false))
    return () => controller.abort()
  }, [classId])

  useEffect(() => {
    if (!showAddForm || debouncedSearch.trim().length < 2) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- limpa resultados quando a busca fica curta demais
      setSearchResults([])
      return
    }
    const controller = new AbortController()
    listStudents({ status: 'ativo', query: debouncedSearch.trim(), page: 1, pageSize: 10, signal: controller.signal })
      .then((result) => setSearchResults(result.items))
      .catch(() => {})
    return () => controller.abort()
  }, [debouncedSearch, showAddForm])

  async function handleAdd(studentId: string) {
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

  function handleExportPdf() {
    if (!enrollments) return
    const active = enrollments.filter((enrollment) => enrollment.status === 'ativa')
    const doc = createBrandedPdf(
      className,
      `${active.length} estudante${active.length === 1 ? '' : 's'} ativo${active.length === 1 ? '' : 's'}`,
    )
    autoTable(doc, {
      startY: 34,
      margin: { left: 14, right: 14 },
      head: [['#', 'Estudante', 'Matriculado em']],
      body: active.map((enrollment, index) => [
        String(index + 1).padStart(2, '0'),
        studentNames[enrollment.student_id] ?? 'Estudante',
        new Date(enrollment.created_at).toLocaleDateString('pt-BR'),
      ]),
      columnStyles: { 0: { cellWidth: 12 }, 2: { cellWidth: 36 } },
      ...PDF_TABLE_THEME,
    })
    addPdfFooter(doc)
    doc.save(`${className.replace(/[^\w\- ]/g, '').trim() || 'turma'}-matriculas.pdf`)
  }

  return (
    <div className="flex flex-col gap-6">
      {occupancy && (
        <div className="grid gap-4 md:grid-cols-2">
          <MetricCard label="Vagas ocupadas" value={occupancy.enrolled} icon={ClipboardList} tone="blue" />
          <MetricCard label="Capacidade" value={occupancy.capacity} icon={ClipboardList} tone="amber" />
        </div>
      )}

      {occupancy && (
        <div className="liquid-glass border-l-2 border-l-brand-green p-6">
          <OccupancyBar capacity={occupancy.capacity} enrolled={occupancy.enrolled} />
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/35">Lista da turma</p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">Estudantes matriculados</h2>
        </div>
        <div className="flex items-center gap-2">
          {enrollments && enrollments.length > 0 && (
            <Button variant="secondary" onClick={handleExportPdf} className="gap-2">
              <Download className="h-4 w-4" aria-hidden="true" />
              Exportar PDF
            </Button>
          )}
          {canCreateEnrollments && (
            <Button variant="secondary" onClick={() => setShowAddForm((value) => !value)} className="gap-2">
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Matricular estudante
            </Button>
          )}
        </div>
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
                <span className="flex min-w-0 items-center gap-4">
                  <span className="font-display text-xs text-white/30">{String(index + 1).padStart(2, '0')}</span>
                  <span className="break-words text-sm text-white">
                    {studentNames[enrollment.student_id] ?? 'Carregando…'}
                  </span>
                </span>
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
                      {enrollment.status === 'ativa' ? 'Remover' : 'Reativar'}
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
