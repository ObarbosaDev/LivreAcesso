import { Eye, EyeOff, Lock, Mail, TriangleAlert } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { publicEnv } from '@/shared/config/env'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { FullScreenState } from '@/shared/ui/FullScreenState'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { AuthHero, AuthPanel } from '@/widgets/AuthHero'
import { ThemeToggle } from '@/shared/ui/ThemeToggle'

export function LoginPage() {
  usePageTitle('Entrar')
  const { status, signIn } = useAuth()
  const location = useLocation()
  const formId = useId()
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({})
  const [capsLockOn, setCapsLockOn] = useState(false)

  useEffect(() => {
    emailRef.current?.focus()
  }, [])

  if (!publicEnv) {
    return (
      <FullScreenState
        title="Configuração indisponível"
        description="As variáveis públicas do frontend não foram definidas. Avise a equipe técnica antes de tentar entrar."
      />
    )
  }

  if (status === 'signed-in') {
    const from = (location.state as { from?: Location })?.from
    return <Navigate to={from?.pathname ?? '/'} replace />
  }

  function handlePasswordKeyEvent(event: KeyboardEvent<HTMLInputElement>) {
    setCapsLockOn(event.getModifierState('CapsLock'))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setFormError(null)
    setFieldErrors({})

    if (!email) {
      setFieldErrors({ email: 'Informe o e-mail da sua conta.' })
      emailRef.current?.focus()
      return
    }
    if (!password) {
      setFieldErrors({ password: 'Informe sua senha.' })
      passwordRef.current?.focus()
      return
    }

    setSubmitting(true)
    const { error } = await signIn(email, password)
    setSubmitting(false)
    if (error) {
      setFormError(error)
      passwordRef.current?.focus()
    }
  }

  return (
    <div className="relative flex min-h-screen bg-ink">
      <div className="absolute right-6 top-6 z-10"><ThemeToggle /></div>
      <AuthHero
        title={
          <>
            Acesso da
            <br />
            equipe
          </>
        }
        description="Entre para acompanhar estudantes, turmas e matrículas do instituto em um só lugar."
      />

      <AuthPanel>
        <h2 className="font-display text-[1.75rem] font-semibold tracking-tight text-white">Entrar</h2>
        <p className="mt-2 text-sm text-white/50">
          Use a conta cadastrada pela coordenação do instituto.
        </p>

        <form id={formId} onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-5">
          <Input
            ref={emailRef}
            label="E-mail"
            type="email"
            autoComplete="username"
            spellCheck={false}
            autoCapitalize="none"
            value={email}
            onChange={(event) => { setEmail(event.target.value); setFieldErrors((current) => ({ ...current, email: undefined })); setFormError(null) }}
            error={fieldErrors.email}
            disabled={submitting}
            icon={<Mail className="h-4 w-4" aria-hidden="true" />}
          />

          <div>
            <div className="relative">
              <Input
                ref={passwordRef}
                label="Senha"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(event) => { setPassword(event.target.value); setFieldErrors((current) => ({ ...current, password: undefined })); setFormError(null) }}
                onKeyDown={handlePasswordKeyEvent}
                onKeyUp={handlePasswordKeyEvent}
                disabled={submitting}
                className="pr-12"
                icon={<Lock className="h-4 w-4" aria-hidden="true" />}
                error={fieldErrors.password}
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
              <p className="mt-2 flex items-center gap-1.5 text-xs text-warning">
                <TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />
                Caps Lock está ativado.
              </p>
            )}
            <Link
              to="/esqueci-senha"
              className="mt-2 inline-block text-xs font-medium text-white/50 transition hover:text-brand-green"
            >
              Esqueceu a senha?
            </Link>
          </div>

          {formError && (
            <p role="alert" className="text-sm text-danger">
              {formError}
            </p>
          )}

          <Button type="submit" loading={submitting} className="mt-2 w-full">
            {submitting ? 'Entrando…' : 'Entrar'}
          </Button>
        </form>

        <p className="mt-8 text-xs leading-relaxed text-white/35">
          O acesso é administrado pela coordenação. Procure a equipe do instituto se precisar de uma
          conta.
        </p>
      </AuthPanel>
    </div>
  )
}
