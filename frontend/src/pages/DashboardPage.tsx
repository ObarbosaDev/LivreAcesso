import { CalendarRange, ClipboardList, Users } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { ROLE_LABELS } from '@/entities/profile/types'
import { usePageTitle } from '@/shared/lib/usePageTitle'

interface ModuleLink {
  to: string
  icon: LucideIcon
  title: string
  description: string
}

const MODULE_LINKS: ModuleLink[] = [
  {
    to: '/estudantes',
    icon: Users,
    title: 'Estudantes',
    description: 'Cadastro, responsáveis e situação de cada participante.',
  },
  {
    to: '/turmas',
    icon: CalendarRange,
    title: 'Turmas',
    description: 'Modalidades, horários, capacidade e ocupação.',
  },
  {
    to: '/matriculas',
    icon: ClipboardList,
    title: 'Matrículas',
    description: 'Vínculo entre estudante e turma, com histórico.',
  },
]

/**
 * Painel inicial. Nenhum número é inventado: até existir um endpoint de
 * indicadores, a tela mostra só a saudação e os atalhos para as áreas que
 * já têm API real por trás.
 */
export function DashboardPage() {
  usePageTitle('Início')
  const { profile } = useAuth()
  const firstName = profile?.full_name.split(' ')[0] ?? ''

  return (
    <div className="max-w-3xl">
      <h1 className="font-display text-2xl font-semibold text-white">Olá, {firstName}</h1>
      <p className="mt-2 text-sm text-white/55">
        Você está conectado como {profile ? ROLE_LABELS[profile.role].toLowerCase() : '—'}. Este
        painel vai reunir indicadores reais conforme cada área ganha interface.
      </p>

      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {MODULE_LINKS.map(({ to, icon: Icon, title, description }) => (
          <Link
            key={to}
            to={to}
            className="liquid-glass group flex flex-col gap-3 rounded-2xl p-5 transition hover:-translate-y-0.5 hover:border-brand-green/40"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-green/12">
              <Icon className="h-5 w-5 text-brand-green" aria-hidden="true" />
            </span>
            <span className="font-display text-base font-semibold text-white">{title}</span>
            <span className="text-sm text-white/55">{description}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
