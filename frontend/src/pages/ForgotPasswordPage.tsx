import { ArrowLeft, Mail } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { publicEnv } from '@/shared/config/env'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { FullScreenState } from '@/shared/ui/FullScreenState'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { AuthHero, AuthPanel } from '@/widgets/AuthHero'

export function ForgotPasswordPage() {
  usePageTitle('Recuperar senha')
  const { requestPasswordReset } = useAuth()
  const formId = useId()
  const emailRef = useRef<HTMLInputElement>(null)

  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  if (!publicEnv) {
    return (
      <FullScreenState
        title="Configuração indisponível"
        description="As variáveis públicas do frontend não foram definidas. Avise a equipe técnica antes de tentar entrar."
      />
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setFormError(null)

    if (!email) {
      setFormError('Informe o e-mail da sua conta.')
      emailRef.current?.focus()
      return
    }

    setSubmitting(true)
    await requestPasswordReset(email)
    setSubmitting(false)
    setSent(true)
  }

  return (
    <div className="flex min-h-screen bg-ink">
      <AuthHero
        title="Recuperar o acesso"
        description="Vamos enviar um link seguro para você escolher uma nova senha."
        showModules={false}
      />

      <AuthPanel>
        <Link
          to="/entrar"
          className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-white/50 transition hover:text-white"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          Voltar para entrar
        </Link>

        {sent ? (
          <>
            <h2 className="font-display text-[1.75rem] font-semibold tracking-tight text-white">
              Confira seu e-mail
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-white/60">
              Se <strong className="text-white/80">{email}</strong> estiver cadastrado, enviamos um
              link para redefinir a senha. Ele expira em pouco tempo por segurança.
            </p>
          </>
        ) : (
          <>
            <h2 className="font-display text-[1.75rem] font-semibold tracking-tight text-white">
              Esqueceu a senha?
            </h2>
            <p className="mt-2 text-sm text-white/50">
              Informe o e-mail cadastrado pela coordenação do instituto.
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
                onChange={(event) => setEmail(event.target.value)}
                disabled={submitting}
                icon={<Mail className="h-4 w-4" aria-hidden="true" />}
              />

              {formError && (
                <p role="alert" className="text-sm text-danger">
                  {formError}
                </p>
              )}

              <Button type="submit" loading={submitting} className="mt-2 w-full">
                {submitting ? 'Enviando…' : 'Enviar link de recuperação'}
              </Button>
            </form>
          </>
        )}
      </AuthPanel>
    </div>
  )
}
