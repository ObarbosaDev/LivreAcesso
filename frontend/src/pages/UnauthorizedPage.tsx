import { useAuth } from '@/app/providers/AuthProvider'
import { Button } from '@/shared/ui/Button'
import { usePageTitle } from '@/shared/lib/usePageTitle'

/** Mostrado quando a conta existe no Supabase mas o perfil ainda não tem papel definido ou está desativado. */
export function UnauthorizedPage() {
  usePageTitle('Sem acesso')
  const { profile, signOut } = useAuth()

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink px-6">
      <div className="liquid-glass max-w-md rounded-2xl p-8 text-center">
        <h1 className="font-display text-xl font-semibold text-white">Seu acesso ainda não está liberado</h1>
        <p className="mt-3 text-sm leading-relaxed text-white/60">
          {profile
            ? 'A coordenação precisa definir um papel e ativar sua conta antes de você usar o sistema.'
            : 'Não encontramos um perfil operacional ativo para esta conta.'}
        </p>
        <Button variant="secondary" onClick={() => void signOut()} className="mt-6 w-full">
          Sair
        </Button>
      </div>
    </div>
  )
}
