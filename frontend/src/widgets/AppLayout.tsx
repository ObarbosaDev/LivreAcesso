import { CalendarRange, ClipboardList, LayoutDashboard, Menu, Users, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { ROLE_LABELS } from '@/entities/profile/types'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/Button'
import { LogoMark } from '@/shared/ui/LogoMark'

const NAV_ITEMS = [
  { to: '/', label: 'Início', icon: LayoutDashboard, end: true },
  { to: '/estudantes', label: 'Estudantes', icon: Users },
  { to: '/turmas', label: 'Turmas', icon: CalendarRange },
  { to: '/matriculas', label: 'Matrículas', icon: ClipboardList },
]

/** Casca fixa do sistema: menu lateral (drawer no celular), cabeçalho e área de conteúdo. */
export function AppLayout() {
  const { profile, signOut } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const navLinks = (
    <nav aria-label="Navegação principal" className="flex flex-1 flex-col gap-1 px-3">
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setDrawerOpen(false)}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition',
              isActive ? 'bg-brand-green/15 text-brand-green' : 'text-white/65 hover:bg-white/6 hover:text-white',
            )
          }
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
          {label}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen bg-ink">
      <a
        href="#conteudo-principal"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-brand-green focus:px-4 focus:py-2 focus:text-ink"
      >
        Pular para o conteúdo
      </a>

      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-white/8 bg-surface py-6 lg:flex">
        <div className="mb-8 px-4">
          <LogoMark />
        </div>
        {navLinks}
      </aside>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Fechar menu"
            className="absolute inset-0 bg-black/60"
            onClick={() => setDrawerOpen(false)}
          />
          <aside className="liquid-glass absolute inset-y-0 left-0 flex w-72 flex-col py-6">
            <div className="mb-8 flex items-center justify-between px-4">
              <LogoMark />
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Fechar menu"
                className="flex h-8 w-8 items-center justify-center rounded-md text-white/60 hover:text-white"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            {navLinks}
          </aside>
        </div>
      )}

      <div className="flex min-h-screen flex-col lg:pl-64">
        <header className="flex h-16 items-center justify-between border-b border-white/8 px-4 sm:px-6">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Abrir menu"
            className="flex h-9 w-9 items-center justify-center rounded-md text-white/70 hover:text-white lg:hidden"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>

          <div className="ml-auto flex items-center gap-4">
            {profile && (
              <div className="text-right">
                <p className="text-sm font-medium text-white">{profile.full_name}</p>
                <p className="text-xs text-white/45">{ROLE_LABELS[profile.role]}</p>
              </div>
            )}
            <Button variant="secondary" onClick={() => void signOut()}>
              Sair
            </Button>
          </div>
        </header>

        <main id="conteudo-principal" className="flex-1 px-4 py-8 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
