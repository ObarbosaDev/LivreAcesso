import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { LandingPage } from '@/pages/LandingPage'

vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ status: 'signed-out' }),
}))

describe('LandingPage', () => {
  it('apresenta o instituto e os dois projetos reais, com acesso só pelo Entrar da navbar', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Cuidado que abre caminhos.' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sobre o Instituto' })).toBeInTheDocument()
    expect(screen.getAllByText('SoulBallet').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Livre Acesso ao Esporte').length).toBeGreaterThan(0)
    // Só um ponto de acesso ao sistema: o "Entrar" da navbar.
    expect(screen.getAllByRole('link', { name: /Entrar/ })).toHaveLength(1)
    expect(screen.getByRole('link', { name: 'Pular para o conteúdo' })).toHaveAttribute('href', '#conteudo-principal')
  })
})
