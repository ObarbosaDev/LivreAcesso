import { BarChart3, CalendarRange, ClipboardList, LayoutDashboard, Menu, Search, ShieldCheck, Users, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { ROLE_LABELS } from '@/entities/profile/types'
import { cn } from '@/shared/lib/cn'
import { Button } from '@/shared/ui/Button'
import { LogoMark } from '@/shared/ui/LogoMark'
import { ThemeToggle } from '@/shared/ui/ThemeToggle'

const NAV_ITEMS = [
  { to: '/', label: 'Início', icon: LayoutDashboard, end: true },
  { to: '/estudantes', label: 'Estudantes', icon: Users },
  { to: '/turmas', label: 'Turmas', icon: CalendarRange },
  { to: '/matriculas', label: 'Matrículas', icon: ClipboardList },
  { to: '/relatorios', label: 'Relatórios', icon: BarChart3 },
]

/** Casca fixa do sistema: menu lateral (drawer no celular), cabeçalho e área de conteúdo. */
function SidebarStatus() {
  const today = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' }).format(new Date())
  const shortcuts = [{ to: '/estudantes/novo', label: 'Novo estudante', code: '01' }, { to: '/turmas/nova', label: 'Nova turma', code: '02' }, { to: '/relatorios', label: 'Abrir relatórios', code: '03' }]
  return <div className="mt-auto mx-4 mb-3 border border-brand-green/20 bg-brand-green/[.06] p-4"><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand-green">Atalhos de operação</p><span className="text-[10px] text-white/35">{today}</span></div><div className="mt-4 border-t border-brand-green/15 pt-2">{shortcuts.map(({ to, label, code }) => <Link key={to} to={to} className="group flex items-center gap-3 border-b border-brand-green/10 py-3 text-xs text-white/55 transition last:border-0 hover:text-brand-green"><span className="font-display text-[10px] text-brand-green/70">{code}</span><span className="flex-1">{label}</span><span className="text-white/25 transition group-hover:text-brand-green">→</span></Link>)}</div><p className="mt-3 text-[10px] uppercase tracking-[0.12em] text-white/30">Ctrl K · busca rápida</p></div>
}

export function AppLayout() {
  const { profile, signOut } = useAuth()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)
  const [commandQuery, setCommandQuery] = useState('')

  const navItems = useMemo(() => profile?.capabilities.includes('profiles:manage') ? [...NAV_ITEMS, { to: '/equipe', label: 'Equipe', icon: ShieldCheck }] : NAV_ITEMS, [profile?.capabilities])

  const commandItems = useMemo(() => navItems.filter(({ label }) => label.toLowerCase().includes(commandQuery.toLowerCase())), [commandQuery, navItems])

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandOpen(true)
      }
      if (event.key === 'Escape') setCommandOpen(false)
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [])

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
        <SidebarStatus />
        <div className="hidden mx-4 rounded-2xl border border-brand-green/15 bg-brand-green/[.06] p-4">
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

          <button type="button" onClick={() => setCommandOpen(true)} className="hidden h-10 min-w-64 items-center gap-3 border border-white/10 bg-surface px-3 text-left text-sm text-white/35 transition hover:border-brand-green/40 hover:text-white/60 md:flex"><Search className="h-4 w-4" aria-hidden="true" /><span className="flex-1">Ir para uma área...</span><kbd className="border border-white/10 px-1.5 py-0.5 text-[10px] text-white/35">CTRL K</kbd></button>
          <div className="ml-auto flex items-center gap-3">
            <ThemeToggle />
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

      {commandOpen && <div className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[16vh]"><button type="button" aria-label="Fechar busca" className="absolute inset-0 bg-black/70" onClick={() => setCommandOpen(false)} /><div className="relative w-full max-w-xl border border-white/15 bg-surface shadow-2xl" role="dialog" aria-modal="true" aria-label="Busca de áreas"><div className="flex items-center gap-3 border-b border-white/10 px-4"><Search className="h-4 w-4 text-brand-green" aria-hidden="true" /><input value={commandQuery} onChange={(event) => setCommandQuery(event.target.value)} placeholder="Buscar área do sistema..." className="h-14 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/35" /></div><div className="p-2">{commandItems.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => { setCommandOpen(false); setCommandQuery('') }} className="flex items-center gap-3 px-3 py-3 text-sm text-white/65 transition hover:bg-brand-green/10 hover:text-brand-green"><Icon className="h-4 w-4" aria-hidden="true" />{label}<span className="ml-auto text-xs text-white/25">Abrir</span></NavLink>)}{commandItems.length === 0 && <p className="px-3 py-8 text-center text-sm text-white/40">Nenhuma área encontrada.</p>}</div></div></div>}
    </div>
  )
}
