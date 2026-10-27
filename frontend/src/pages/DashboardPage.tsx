import { useAuth } from '@/app/providers/AuthProvider'
import { usePageTitle } from '@/shared/lib/usePageTitle'

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
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl font-semibold text-white">Olá, {firstName}</h1>
      <p className="mt-2 text-sm text-white/55">
        Este painel vai reunir estudantes, turmas e matrículas conforme cada área ganha interface.
      </p>
    </div>
  )
}
