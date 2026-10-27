import { CalendarRange, ClipboardList, LayoutDashboard, Menu, ShieldCheck, Users, X } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'

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

  const navItems = profile?.capabilities.includes('profiles:manage')
    ? [...NAV_ITEMS, { to: '/equipe', label: 'Equipe', icon: ShieldCheck }]
    : NAV_ITEMS

  const navLinks = (
    <nav aria-label="Navegação principal" className="flex flex-1 flex-col gap-2 px-4">
      {navItems.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setDrawerOpen(false)}
          className={({ isActive }) =>
            cn(
              'group flex items-center gap-3 rounded-xl border border-transparent px-3 py-3 text-sm font-medium transition',
              isActive ? 'border-brand-green/15 bg-brand-green/12 text-brand-green shadow-[inset_3px_0_var(--color-brand-green)]' : 'text-white/55 hover:border-white/8 hover:bg-white/[.04] hover:text-white',
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

      <aside className="fixed inset-y-0 left-0 hidden w-[272px] flex-col border-r border-white/8 bg-surface py-6 lg:flex">
        <div className="mb-10 px-6">
          <LogoMark />
        </div>
        <div className="mb-4 px-6 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/30">Operação</div>
        {navLinks}
        <div className="mt-auto mx-4 rounded-2xl border border-brand-green/15 bg-brand-green/[.06] p-4">
          <p className="text-xs font-semibold text-brand-green">Livre Acesso</p>
          <p className="mt-1 text-xs leading-5 text-white/40">Gestão com cuidado, dados e presença.</p>
        </div>
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

      <div className="flex min-h-screen flex-col lg:pl-[272px]">
        <header className="flex h-[76px] items-center justify-between border-b border-white/8 bg-ink/75 px-4 backdrop-blur-sm sm:px-8">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Abrir menu"
            className="flex h-9 w-9 items-center justify-center rounded-md text-white/70 hover:text-white lg:hidden"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>

          <div className="ml-auto flex items-center gap-3">
            {profile && (
              <Link to="/perfil" className="group flex items-center gap-3 rounded-full py-1 pl-2 pr-3 transition hover:bg-white/[.05]">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-green text-sm font-bold text-ink">{profile.full_name.slice(0, 1).toUpperCase()}</span>
                <span className="hidden text-left sm:block"><p className="text-sm font-semibold text-white group-hover:text-brand-green">{profile.full_name}</p><p className="text-xs text-white/40">{ROLE_LABELS[profile.role]}</p></span>
              </Link>
            )}
            <Button variant="secondary" onClick={() => void signOut()}>Sair</Button>
          </div>
        </header>

        <main id="conteudo-principal" className="flex-1 px-4 py-8 sm:px-8 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
