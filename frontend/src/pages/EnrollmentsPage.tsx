import { ClipboardList, Loader2, Search, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'

import { getClassOccupancy, listClasses } from '@/features/classes/api'
import { createEnrollment, listEnrollments } from '@/features/enrollments/api'
import { getStudentSummary, listStudents } from '@/features/students/api'
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

/**
 * Matrícula é escopada por turma: a API não devolve nome de aluno nem de
 * turma dentro da matrícula (só IDs), então a tela parte da turma — que já
 * tem nome legível — e resolve o nome de cada aluno sob demanda.
 */
export function EnrollmentsPage() {
  usePageTitle('Matrículas')

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
        Promise.all(
          enrollmentPage.items.map((enrollment) =>
            getStudentSummary(enrollment.student_id, controller.signal)
              .then((student) => [enrollment.student_id, student.full_name] as const)
              .catch(() => [enrollment.student_id, 'Estudante não encontrado'] as const),
          ),
        ).then((pairs) => setStudentNames(Object.fromEntries(pairs)))
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

  async function handleAdd(studentId: string) {
    if (adding) return
    setAdding(true)
    setAddError(null)
    try {
      await createEnrollment(studentId, selectedClassId)
      setShowAddForm(false)
      setSearchQuery('')
      setSearchResults([])
      // Recarrega a lista e a ocupação para refletir a matrícula recém-criada.
      const [enrollmentPage, occ] = await Promise.all([
        listEnrollments({ classId: selectedClassId, page: 1, pageSize: 50 }),
        getClassOccupancy(selectedClassId),
      ])
      setEnrollments(enrollmentPage.items)
      setOccupancy({ capacity: occ.capacity, enrolled: occ.enrolled })
      const pairs = await Promise.all(
        enrollmentPage.items.map((enrollment) =>
          getStudentSummary(enrollment.student_id)
            .then((student) => [enrollment.student_id, student.full_name] as const)
            .catch(() => [enrollment.student_id, 'Estudante não encontrado'] as const),
        ),
      )
      setStudentNames(Object.fromEntries(pairs))
    } catch (caught) {
      setAddError(friendlyMessage(caught))
    } finally {
      setAdding(false)
    }
  }

  return (
    <div>
      <h1 className="font-display text-2xl font-semibold text-white">Matrículas</h1>
      <p className="mt-2 text-sm text-white/55">Escolha uma turma para ver e gerenciar as matrículas.</p>

      <div className="mt-6 max-w-xs">
        <label htmlFor="class-select" className="text-sm font-medium text-white">
          Turma
        </label>
        <select
          id="class-select"
          value={selectedClassId}
          onChange={(event) => setSelectedClassId(event.target.value)}
          disabled={!classes}
          className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/5 px-4 text-white outline-none transition focus:border-brand-green focus:bg-white/8 focus:ring-4 focus:ring-brand-green/15"
        >
          <option value="" className="bg-surface">
            {classes ? 'Selecione uma turma' : 'Carregando turmas…'}
          </option>
          {classes?.map((schoolClass) => (
            <option key={schoolClass.id} value={schoolClass.id} className="bg-surface">
              {schoolClass.name}
            </option>
          ))}
        </select>
      </div>

      {!selectedClassId && classes && classes.length === 0 && (
        <div className="liquid-glass mt-8 flex flex-col items-center gap-3 rounded-2xl p-12 text-center">
          <ClipboardList className="h-6 w-6 text-white/40" aria-hidden="true" />
          <p className="text-sm text-white/55">
            Nenhuma turma ativa ainda. Crie uma turma antes de matricular um estudante.
          </p>
        </div>
      )}

      {selectedClassId && (
        <div className="mt-8 flex flex-col gap-6">
          {occupancy && selectedClass && (
            <div className="liquid-glass max-w-xs rounded-2xl p-5">
              <p className="text-sm font-medium text-white">{selectedClass.name}</p>
              <div className="mt-3">
                <OccupancyBar capacity={occupancy.capacity} enrolled={occupancy.enrolled} />
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <h2 className="font-display text-base font-semibold text-white">Estudantes matriculados</h2>
            <Button
              variant="secondary"
              onClick={() => setShowAddForm((value) => !value)}
              className="gap-2"
            >
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Nova matrícula
            </Button>
          </div>

          {showAddForm && (
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
            <div className="liquid-glass flex flex-col items-center gap-3 rounded-2xl p-10 text-center">
              <ClipboardList className="h-6 w-6 text-white/40" aria-hidden="true" />
              <p className="text-sm text-white/55">Esta turma ainda não possui estudantes.</p>
            </div>
          )}

          {!loading && !error && enrollments && enrollments.length > 0 && (
            <ul className="flex flex-col gap-2">
              {enrollments.map((enrollment) => (
                <li
                  key={enrollment.id}
                  className="liquid-glass flex items-center justify-between rounded-xl px-4 py-3"
                >
                  <span className="text-sm text-white">
                    {studentNames[enrollment.student_id] ?? 'Carregando…'}
                  </span>
                  <StatusBadge
                    label={ENROLLMENT_STATUS_LABELS[enrollment.status]}
                    tone={enrollment.status === 'ativa' ? 'success' : 'neutral'}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
