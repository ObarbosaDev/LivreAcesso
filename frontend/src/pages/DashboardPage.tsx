import { ArrowUpRight, CalendarDays, ClipboardList, Clock3, Plus, Users, UsersRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { listClasses } from '@/features/classes/api'
import { listStudents } from '@/features/students/api'
import { ROLE_LABELS } from '@/entities/profile/types'
import { usePageTitle } from '@/shared/lib/usePageTitle'

interface Counts { activeStudents: number; activeClasses: number }

const QUICK_ACTIONS = [
  { to: '/estudantes/novo', label: 'Cadastrar estudante', icon: UsersRound },
  { to: '/turmas/nova', label: 'Criar turma', icon: CalendarDays },
  { to: '/matriculas', label: 'Ver matrículas', icon: ClipboardList },
]

export function DashboardPage() {
  usePageTitle('Início')
  const { profile } = useAuth()
  const firstName = profile?.full_name.split(' ')[0] ?? 'equipe'
  const [counts, setCounts] = useState<Counts | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      listStudents({ status: 'ativo', page: 1, pageSize: 1, signal: controller.signal }),
      listClasses({ active: true, page: 1, pageSize: 1, signal: controller.signal }),
    ]).then(([students, classes]) => setCounts({ activeStudents: students.total, activeClasses: classes.total })).catch(() => {})
    return () => controller.abort()
  }, [])

  return (
    <div className="page-enter mx-auto max-w-[1400px] pb-12">
      <section className="panel-grid relative overflow-hidden rounded-[2rem] border border-white/10 bg-surface px-6 py-8 sm:px-10 sm:py-10">
        <div className="pointer-events-none absolute -right-20 -top-24 h-80 w-80 rounded-full border border-brand-green/20" />
        <div className="pointer-events-none absolute -right-4 -top-8 h-48 w-48 rounded-full border border-brand-green/10" />
        <div className="relative max-w-2xl">
          <p className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand-green"><span className="h-2 w-2 rounded-full bg-brand-green shadow-[0_0_16px_var(--color-brand-green)]" />Central de operação</p>
          <h1 className="font-display text-4xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">Bom dia, {firstName}.</h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-white/55">Uma visão clara do que está acontecendo no Instituto Livre Acesso, com os próximos passos da equipe sempre à mão.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            {QUICK_ACTIONS.map(({ to, label, icon: Icon }) => <Link key={to} to={to} className="group inline-flex items-center gap-2 rounded-full bg-brand-green px-4 py-2.5 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:bg-brand-green-soft"><Icon className="h-4 w-4" aria-hidden="true" />{label}<ArrowUpRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden="true" /></Link>)}
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-3" aria-label="Indicadores principais">
        <MetricCard label="Estudantes ativos" value={counts?.activeStudents} icon={Users} accent="green" />
        <MetricCard label="Turmas em andamento" value={counts?.activeClasses} icon={CalendarDays} accent="amber" />
        <MetricCard label="Matrículas hoje" value={0} icon={ClipboardList} accent="blue" />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_.65fr]">
        <div className="liquid-glass rounded-3xl p-6 sm:p-7">
          <div className="flex items-start justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/40">Visão do instituto</p><h2 className="mt-2 font-display text-xl font-semibold text-white">Crescimento da operação</h2></div><span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/40">Últimos 6 meses</span></div>
          <div className="mt-6 rounded-2xl bg-ink/45 p-4">
            <svg viewBox="0 0 760 220" className="h-56 w-full" role="img" aria-label="Gráfico de evolução de estudantes e turmas">
              <defs><linearGradient id="area-green" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#7ed957" stopOpacity=".28"/><stop offset="1" stopColor="#7ed957" stopOpacity="0"/></linearGradient></defs>
              {[32, 78, 124, 170].map((y) => <line key={y} x1="24" x2="736" y1={y} y2={y} stroke="rgba(255,255,255,.07)" />)}
              <path d="M24 170 C130 170 130 170 238 170 S350 170 466 170 S620 170 736 170 L736 190 L24 190Z" fill="url(#area-green)" />
              <path d="M24 170 C130 170 130 170 238 170 S350 170 466 170 S620 170 736 170" fill="none" stroke="#7ed957" strokeWidth="3" strokeLinecap="round" />
              {[24, 166, 308, 450, 592, 736].map((x, index) => <g key={x}><circle cx={x} cy="170" r="5" fill="#101511" stroke="#7ed957" strokeWidth="2" /><text x={x} y="213" textAnchor="middle" fill="rgba(255,255,255,.38)" fontSize="11">{['Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out'][index]}</text></g>)}
            </svg>
            <div className="mt-2 flex items-center gap-5 text-xs text-white/40"><span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-brand-green" /> Estudantes ativos</span><span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-white/25" /> Turmas ativas</span></div>
          </div>
        </div>
        <div className="liquid-glass rounded-3xl p-6 sm:p-7"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/40">Distribuição atual</p><h2 className="mt-2 font-display text-xl font-semibold text-white">Status dos estudantes</h2><div className="mt-8 flex items-center gap-6"><div className="relative flex h-32 w-32 shrink-0 items-center justify-center rounded-full" style={{ background: 'conic-gradient(#7ed957 0deg 0deg, rgba(255,255,255,.08) 0deg 360deg)' }}><div className="flex h-24 w-24 flex-col items-center justify-center rounded-full bg-surface"><span className="font-display text-2xl font-semibold text-white">{counts?.activeStudents ?? '—'}</span><span className="text-[10px] uppercase tracking-wider text-white/35">ativos</span></div></div><div className="space-y-3 text-sm"><div><p className="text-white/45">Ativos</p><p className="font-semibold text-brand-green">{counts?.activeStudents ?? '—'}</p></div><div><p className="text-white/45">Inativos</p><p className="font-semibold text-white">0</p></div></div></div><p className="mt-8 border-t border-white/8 pt-4 text-xs leading-5 text-white/35">A distribuição será preenchida automaticamente conforme os cadastros forem realizados.</p></div>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_.8fr]">
        <div className="liquid-glass rounded-3xl p-6 sm:p-7">
          <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/40">Agenda da operação</p><h2 className="mt-2 font-display text-xl font-semibold text-white">Próximas atividades</h2></div><Clock3 className="h-5 w-5 text-white/35" aria-hidden="true" /></div>
          <div className="mt-8 rounded-2xl border border-dashed border-white/12 px-6 py-12 text-center"><CalendarDays className="mx-auto h-8 w-8 text-brand-green/70" aria-hidden="true" /><p className="mt-4 text-sm font-medium text-white">A agenda começa aqui</p><p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-white/45">Crie turmas e horários para acompanhar a rotina do instituto nesta área.</p><Link to="/turmas/nova" className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-brand-green hover:text-brand-green-soft">Criar primeira turma <ArrowUpRight className="h-4 w-4" aria-hidden="true" /></Link></div>
        </div>
        <div className="liquid-glass rounded-3xl p-6 sm:p-7"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-white/40">Acesso rápido</p><h2 className="mt-2 font-display text-xl font-semibold text-white">Áreas do sistema</h2><div className="mt-6 space-y-2">{[{ to: '/estudantes', label: 'Estudantes', note: 'Cadastros e responsáveis', icon: UsersRound }, { to: '/turmas', label: 'Turmas', note: 'Horários e ocupação', icon: CalendarDays }, { to: '/matriculas', label: 'Matrículas', note: 'Vínculos e histórico', icon: ClipboardList }].map(({ to, label, note, icon: Icon }) => <Link key={to} to={to} className="group flex items-center gap-3 rounded-2xl border border-transparent px-3 py-3 transition hover:border-white/10 hover:bg-white/[.04]"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[.06] text-brand-green transition group-hover:bg-brand-green group-hover:text-ink"><Icon className="h-5 w-5" aria-hidden="true" /></span><span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-white">{label}</span><span className="block text-xs text-white/40">{note}</span></span><ArrowUpRight className="h-4 w-4 text-white/25 transition group-hover:text-brand-green" aria-hidden="true" /></Link>)}</div></div>
      </section>
      <p className="mt-8 text-xs text-white/35">Sessão ativa como {profile ? ROLE_LABELS[profile.role].toLowerCase() : 'usuário autorizado'}.</p>
    </div>
  )
}

function MetricCard({ label, value, icon: Icon, accent }: { label: string; value?: number; icon: typeof Users; accent: 'green' | 'amber' | 'blue' }) {
  const colors = { green: 'text-brand-green bg-brand-green/12', amber: 'text-warning bg-warning/12', blue: 'text-sky-300 bg-sky-300/12' }
  return <div className="page-enter stagger-1 liquid-glass rounded-3xl p-6"><div className="flex items-start justify-between"><span className={`flex h-11 w-11 items-center justify-center rounded-2xl ${colors[accent]}`}><Icon className="h-5 w-5" aria-hidden="true" /></span><Plus className="h-4 w-4 text-white/20" aria-hidden="true" /></div><p className="mt-8 text-sm text-white/50">{label}</p><p className="mt-1 font-display text-4xl font-semibold tracking-[-0.04em] text-white">{value ?? '—'}</p></div>
}
