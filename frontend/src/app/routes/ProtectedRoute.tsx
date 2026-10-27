import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { FullScreenState } from '@/shared/ui/FullScreenState'

/**
 * Autoriza apenas visualmente: o backend continua sendo a autoridade real em
 * cada RPC. Esta proteção evita que a interface mostre uma tela operacional
 * para quem não tem sessão ou perfil ativo, nada além disso.
 */
export function ProtectedRoute() {
  const { status, profile, profileError, isPasswordRecovery } = useAuth()
  const location = useLocation()

  if (isPasswordRecovery) {
    return <Navigate to="/redefinir-senha" replace />
  }

  if (status === 'config-missing') {
    return (
      <FullScreenState
        title="Configuração indisponível"
        description="O acesso não pôde ser inicializado. Avise a equipe técnica."
      />
    )
  }

  if (status === 'loading') {
    return <FullScreenState title="Carregando sessão" description="Só um instante." loading />
  }

  if (status === 'signed-out') {
    return <Navigate to="/entrar" replace state={{ from: location }} />
  }

  if (profileError) {
    return (
      <FullScreenState
        title="Não foi possível carregar seu perfil"
        description={profileError}
        actionHref="/entrar"
        actionLabel="Entrar novamente"
      />
    )
  }

  if (!profile) {
    return <FullScreenState title="Carregando perfil" description="Só um instante." loading />
  }

  if (!profile.active) {
    return <Navigate to="/sem-acesso" replace />
  }

  return <Outlet />
}
