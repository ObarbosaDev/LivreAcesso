import { Eye, EyeOff, Lock, TriangleAlert } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { publicEnv } from '@/shared/config/env'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { FullScreenState } from '@/shared/ui/FullScreenState'
import { PasswordStrengthMeter } from '@/shared/ui/PasswordStrengthMeter'
import { SuccessCheck } from '@/shared/ui/SuccessCheck'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { AuthHero, AuthPanel } from '@/widgets/AuthHero'

export function ResetPasswordPage() {
  usePageTitle('Nova senha')
  const { isPasswordRecovery, updatePassword } = useAuth()
  const formId = useId()
  const passwordRef = useRef<HTMLInputElement>(null)

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [capsLockOn, setCapsLockOn] = useState(false)

  if (!publicEnv) {
    return (
      <FullScreenState
        title="Configuração indisponível"
        description="As variáveis públicas do frontend não foram definidas. Avise a equipe técnica antes de tentar entrar."
      />
    )
  }

  if (!isPasswordRecovery && !done) {
    return <Navigate to="/entrar" replace />
  }

  function handlePasswordKeyEvent(event: KeyboardEvent<HTMLInputElement>) {
    setCapsLockOn(event.getModifierState('CapsLock'))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setFormError(null)

    if (password.length < 8) {
      setFormError('A senha precisa ter pelo menos 8 caracteres.')
      passwordRef.current?.focus()
      return
    }
    if (password !== confirmPassword) {
      setFormError('As senhas não coincidem.')
      return
    }

    setSubmitting(true)
    const { error } = await updatePassword(password)
    setSubmitting(false)
    if (error) {
      setFormError(error)
      return
    }
    setDone(true)
  }

  return (
    <div className="flex min-h-screen bg-ink">
      <AuthHero
        title="Nova senha"
        description="Escolha uma senha que só você conhece. Ela substitui a anterior imediatamente."
        showModules={false}
      />

      <AuthPanel>
        {done ? (
          <div className="flex flex-col items-center text-center">
            <SuccessCheck />
            <h2 className="mt-4 font-display text-[1.75rem] font-semibold tracking-tight text-white">
              Senha atualizada
            </h2>
            <p className="mt-2 text-sm text-white/55">Já pode entrar com a nova senha.</p>
            <Button className="mt-8 w-full" onClick={() => window.location.assign('/entrar')}>
              Ir para o login
            </Button>
          </div>
        ) : (
          <>
            <h2 className="font-display text-[1.75rem] font-semibold tracking-tight text-white">
              Criar nova senha
            </h2>
            <p className="mt-2 text-sm text-white/50">Mínimo de 8 caracteres.</p>

            <form id={formId} onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-5">
              <div>
                <Input
                  ref={passwordRef}
                  label="Nova senha"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  onKeyDown={handlePasswordKeyEvent}
                  onKeyUp={handlePasswordKeyEvent}
                  disabled={submitting}
                  icon={<Lock className="h-4 w-4" aria-hidden="true" />}
                />
                <PasswordStrengthMeter password={password} />
              </div>

              <div className="relative">
                <Input
                  label="Confirmar nova senha"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  disabled={submitting}
                  className="pr-12"
                  icon={<Lock className="h-4 w-4" aria-hidden="true" />}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="absolute right-3 top-9 flex h-8 w-8 items-center justify-center rounded-md text-white/50 transition hover:text-white"
                  aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <Eye className="h-4 w-4" aria-hidden="true" />
                  )}
                </button>
              </div>

              {capsLockOn && (
                <p className="-mt-3 flex items-center gap-1.5 text-xs text-warning">
                  <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
                  Caps Lock está ativado.
                </p>
              )}

              {formError && (
                <p role="alert" className="text-sm text-danger">
                  {formError}
                </p>
              )}

              <Button type="submit" loading={submitting} className="mt-2 w-full">
                {submitting ? 'Salvando…' : 'Salvar nova senha'}
              </Button>
            </form>
          </>
        )}
      </AuthPanel>
    </div>
  )
}
