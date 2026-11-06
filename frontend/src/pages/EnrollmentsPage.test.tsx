import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { EnrollmentsPage } from '@/pages/EnrollmentsPage'

const listClassesMock = vi.fn()
const getClassOccupancyMock = vi.fn()
vi.mock('@/features/classes/api', () => ({
  listClasses: (...args: unknown[]) => listClassesMock(...args),
  getClassOccupancy: (...args: unknown[]) => getClassOccupancyMock(...args),
}))

const listEnrollmentsMock = vi.fn()
const createEnrollmentMock = vi.fn()
const changeEnrollmentStatusMock = vi.fn()
vi.mock('@/features/enrollments/api', () => ({
  listEnrollments: (...args: unknown[]) => listEnrollmentsMock(...args),
  createEnrollment: (...args: unknown[]) => createEnrollmentMock(...args),
  changeEnrollmentStatus: (...args: unknown[]) => changeEnrollmentStatusMock(...args),
}))

const listStudentsMock = vi.fn()
const getStudentNamesMock = vi.fn()
vi.mock('@/features/students/api', () => ({
  listStudents: (...args: unknown[]) => listStudentsMock(...args),
  getStudentNames: (...args: unknown[]) => getStudentNamesMock(...args),
}))

const schoolClass = {
  id: 'class-1',
  modality_id: 'modality-1',
  name: 'Turma A',
  capacity: 20,
  location: 'Sala 1',
  minimum_age: null,
  maximum_age: null,
  schedules: [],
  instructors: [],
  active: true,
}

const enrollment = {
  id: 'enrollment-1',
  student_id: 'student-1',
  class_id: 'class-1',
  status: 'ativa' as const,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

const student = {
  id: 'student-1',
  full_name: 'Sophia Almeida Ramos',
  cpf_masked: '***.***.***-25',
  birth_date: '2015-05-10',
  age: 11,
  status: 'ativo' as const,
  guardian_name: 'Camila Ramos',
  guardian_phone_masked: '(61) *****-1234',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

function setupBaseMocks() {
  listClassesMock.mockResolvedValue({ items: [schoolClass], total: 1, total_pages: 1 })
  listEnrollmentsMock.mockResolvedValue({ items: [enrollment], total: 1, total_pages: 1 })
  getClassOccupancyMock.mockResolvedValue({
    class_id: 'class-1',
    capacity: 20,
    enrolled: 1,
    available: 19,
  })
  getStudentNamesMock.mockResolvedValue({ names: { 'student-1': student.full_name } })
}

describe('EnrollmentsPage', () => {
  it('carrega matrículas e ocupação ao selecionar uma turma', async () => {
    setupBaseMocks()
    render(<EnrollmentsPage />)

    await userEvent.selectOptions(await screen.findByLabelText('Turma'), 'class-1')

    expect(await screen.findByText('Sophia Almeida Ramos')).toBeInTheDocument()
    expect(screen.getByText('1 de 20 vagas ocupadas')).toBeInTheDocument()
  })

  it('busca um estudante e cria a matrícula na turma selecionada', async () => {
    setupBaseMocks()
    const newStudent = { ...student, id: 'student-2', full_name: 'Rafael Costa' }
    listStudentsMock.mockResolvedValue({ items: [newStudent], total: 1, total_pages: 1 })
    createEnrollmentMock.mockResolvedValueOnce({ ...enrollment, id: 'enrollment-2' })

    render(<EnrollmentsPage />)
    await userEvent.selectOptions(await screen.findByLabelText('Turma'), 'class-1')
    await screen.findByText('Sophia Almeida Ramos')

    await userEvent.click(screen.getByRole('button', { name: 'Nova matrícula' }))
    await userEvent.type(screen.getByLabelText('Buscar estudante'), 'Rafael')

    const addButton = await screen.findByRole('button', { name: /Rafael Costa/ })
    await userEvent.click(addButton)

    expect(createEnrollmentMock).toHaveBeenCalledWith('student-2', 'class-1')
    await waitFor(() => expect(listEnrollmentsMock).toHaveBeenCalledTimes(2))
  })

  it('cancela uma matrícula pedindo o motivo num formulário, sem prompt nativo', async () => {
    setupBaseMocks()
    changeEnrollmentStatusMock.mockResolvedValueOnce({ ...enrollment, status: 'cancelada' })

    render(<EnrollmentsPage />)
    await userEvent.selectOptions(await screen.findByLabelText('Turma'), 'class-1')
    await screen.findByText('Sophia Almeida Ramos')

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    const reasonInput = screen.getByLabelText('Motivo do cancelamento')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar cancelamento' }))
    expect(screen.getByText('Informe um motivo com pelo menos 10 caracteres.')).toBeInTheDocument()
    expect(changeEnrollmentStatusMock).not.toHaveBeenCalled()

    await userEvent.type(reasonInput, 'Família mudou de cidade')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar cancelamento' }))

    expect(changeEnrollmentStatusMock).toHaveBeenCalledWith('enrollment-1', 'cancel', {
      expected_updated_at: enrollment.updated_at,
      reason: 'Família mudou de cidade',
    })
  })
})
