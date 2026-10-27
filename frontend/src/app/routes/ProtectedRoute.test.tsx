import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { ProtectedRoute } from '@/app/routes/ProtectedRoute'

const useAuthMock = vi.fn()
vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => useAuthMock(),
}))

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/entrar" element={<p>Tela de login</p>} />
        <Route path="/sem-acesso" element={<p>Sem acesso</p>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<p>Área protegida</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('redireciona para o login quando não há sessão', () => {
    useAuthMock.mockReturnValue({ status: 'signed-out', profile: null, profileError: null })
    renderProtected()
    expect(screen.getByText('Tela de login')).toBeInTheDocument()
  })

  it('redireciona para sem acesso quando o perfil está inativo', () => {
    useAuthMock.mockReturnValue({
      status: 'signed-in',
      profile: { id: '1', full_name: 'Ana', role: 'instrutor', active: false, capabilities: [] },
      profileError: null,
    })
    renderProtected()
    expect(screen.getByText('Sem acesso')).toBeInTheDocument()
  })

  it('mostra a área protegida quando o perfil está ativo', () => {
    useAuthMock.mockReturnValue({
      status: 'signed-in',
      profile: { id: '1', full_name: 'Ana', role: 'coordenador', active: true, capabilities: [] },
      profileError: null,
    })
    renderProtected()
    expect(screen.getByText('Área protegida')).toBeInTheDocument()
  })
})
