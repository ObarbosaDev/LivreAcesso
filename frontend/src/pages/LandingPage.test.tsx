import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { LandingPage } from '@/pages/LandingPage'

vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ status: 'signed-out' }),
}))

describe('LandingPage', () => {
  it('apresenta propósito, modalidades e acesso ao sistema', () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Cuidado que abre caminhos.' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Movimento para descobrir possibilidades.' })).toBeInTheDocument()
    expect(screen.getByText('Jiu-Jitsu')).toBeInTheDocument()
    expect(screen.getByText('Música')).toBeInTheDocument()
    expect(screen.getByText('Balé')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Entrar/ }).length).toBeGreaterThan(0)
  })
})
