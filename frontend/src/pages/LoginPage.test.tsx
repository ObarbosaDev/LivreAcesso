import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { LoginPage } from '@/pages/LoginPage'

const signInMock = vi.fn().mockResolvedValue({ error: null })
vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ status: 'signed-out', signIn: signInMock }),
}))

describe('LoginPage', () => {
  it('impede envio vazio e mostra mensagem de validação', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(screen.getByText('Informe o e-mail da sua conta.')).toBeInTheDocument()
    expect(signInMock).not.toHaveBeenCalled()
  })

  it('alterna a visibilidade da senha', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    const passwordInput = screen.getByLabelText('Senha')
    expect(passwordInput).toHaveAttribute('type', 'password')

    await userEvent.click(screen.getByRole('button', { name: 'Mostrar senha' }))
    expect(passwordInput).toHaveAttribute('type', 'text')
  })

  it('envia e-mail e senha para o provedor de autenticação', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText('E-mail'), 'coordenacao@example.org')
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-valida')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(signInMock).toHaveBeenCalledWith('coordenacao@example.org', 'senha-valida')
  })
})
