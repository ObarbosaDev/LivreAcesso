import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/shared/api/problemDetails'
import type { ProblemDetail } from '@/shared/api/problemDetails'
import { NewStudentPage } from '@/pages/NewStudentPage'

const navigateMock = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigateMock }
})

const registerStudentMock = vi.fn()
vi.mock('@/features/students/api', () => ({
  registerStudent: (...args: unknown[]) => registerStudentMock(...args),
}))

function problem(overrides: Partial<ProblemDetail>): ApiError {
  return new ApiError({
    type: 'urn:livre-acesso:problem:duplicate-cpf',
    title: 'CPF já cadastrado',
    status: 409,
    detail: 'Confira o cadastro existente antes de continuar.',
    code: 'duplicate_cpf',
    request_id: 'req-1',
    errors: [],
    ...overrides,
  })
}

describe('NewStudentPage', () => {
  it('envia o cadastro do estudante e do responsável e navega para a lista', async () => {
    registerStudentMock.mockResolvedValueOnce({ id: 'student-1' })

    render(
      <MemoryRouter>
        <NewStudentPage />
      </MemoryRouter>,
    )

    const [studentName, guardianName] = screen.getAllByLabelText('Nome completo')
    await userEvent.type(studentName, 'Sophia Almeida Ramos')
    await userEvent.type(screen.getByLabelText('CPF (opcional)'), '529.982.247-25')
    await userEvent.type(screen.getByLabelText('Data de nascimento (opcional)'), '2015-05-10')
    await userEvent.type(guardianName, 'Camila Ramos')
    await userEvent.type(screen.getByLabelText('Telefone'), '(61) 99999-1234')
    await userEvent.type(screen.getByLabelText('E-mail (opcional)'), 'camila@example.com')

    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar estudante' }))

    expect(registerStudentMock).toHaveBeenCalledWith({
      full_name: 'Sophia Almeida Ramos',
      cpf: '529.982.247-25',
      birth_date: '2015-05-10',
      guardian: {
        full_name: 'Camila Ramos',
        phone: '(61) 99999-1234',
        email: 'camila@example.com',
      },
    })
    expect(navigateMock).toHaveBeenCalledWith('/estudantes')
  })

  it('cadastra só com o nome, sem CPF, data de nascimento ou responsável', async () => {
    registerStudentMock.mockResolvedValueOnce({ id: 'student-1' })

    render(
      <MemoryRouter>
        <NewStudentPage />
      </MemoryRouter>,
    )

    const [studentName] = screen.getAllByLabelText('Nome completo')
    await userEvent.type(studentName, 'Sophia Almeida Ramos')

    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar estudante' }))

    expect(registerStudentMock).toHaveBeenCalledWith({
      full_name: 'Sophia Almeida Ramos',
      cpf: undefined,
      birth_date: undefined,
      guardian: undefined,
    })
    expect(navigateMock).toHaveBeenCalledWith('/estudantes')
  })

  it('mostra o erro de CPF duplicado no campo certo e não navega', async () => {
    registerStudentMock.mockRejectedValueOnce(
      problem({
        errors: [{ field: 'cpf', code: 'duplicate_cpf', message: 'Este CPF já pertence a um cadastro.' }],
      }),
    )

    render(
      <MemoryRouter>
        <NewStudentPage />
      </MemoryRouter>,
    )

    const [studentName, guardianName] = screen.getAllByLabelText('Nome completo')
    await userEvent.type(studentName, 'Sophia Almeida Ramos')
    await userEvent.type(screen.getByLabelText('CPF (opcional)'), '529.982.247-25')
    await userEvent.type(screen.getByLabelText('Data de nascimento (opcional)'), '2015-05-10')
    await userEvent.type(guardianName, 'Camila Ramos')
    await userEvent.type(screen.getByLabelText('Telefone'), '(61) 99999-1234')

    await userEvent.click(screen.getByRole('button', { name: 'Cadastrar estudante' }))

    expect(await screen.findByText('Este CPF já pertence a um cadastro.')).toBeInTheDocument()
    expect(screen.getByText('Este CPF já pertence a um cadastro existente.')).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('desabilita o botão de envio enquanto a requisição está em andamento', async () => {
    let resolveRequest: (value: { id: string }) => void = () => {}
    registerStudentMock.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )

    render(
      <MemoryRouter>
        <NewStudentPage />
      </MemoryRouter>,
    )

    const [studentName, guardianName] = screen.getAllByLabelText('Nome completo')
    await userEvent.type(studentName, 'Sophia Almeida Ramos')
    await userEvent.type(screen.getByLabelText('CPF (opcional)'), '529.982.247-25')
    await userEvent.type(screen.getByLabelText('Data de nascimento (opcional)'), '2015-05-10')
    await userEvent.type(guardianName, 'Camila Ramos')
    await userEvent.type(screen.getByLabelText('Telefone'), '(61) 99999-1234')

    const submitButton = screen.getByRole('button', { name: 'Cadastrar estudante' })
    await userEvent.click(submitButton)

    expect(screen.getByRole('button', { name: 'Salvando…' })).toBeDisabled()

    resolveRequest({ id: 'student-1' })
    expect(await screen.findByRole('button', { name: 'Cadastrar estudante' })).toBeEnabled()
  })
})
