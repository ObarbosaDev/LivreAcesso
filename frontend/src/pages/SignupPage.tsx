import { ArrowLeft, Eye, EyeOff, Lock, Mail, User } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { publicEnv } from '@/shared/config/env'
import { supabase } from '@/shared/api/supabaseClient'
import { Button } from '@/shared/ui/Button'
import { FullScreenState } from '@/shared/ui/FullScreenState'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { AuthHero, AuthPanel } from '@/widgets/AuthHero'
import type { UserRole } from '@/entities/profile/types'
import { ROLE_LABELS } from '@/entities/profile/types'

/** Papel sugerido no pedido: vira a coluna requested_role, lida pelo gatilho de criação do perfil. */
const REQUESTED_ROLE_DB_VALUE: Record<Exclude<UserRole, 'pendente'>, string> = {
  coordenador: 'coordinator',
  recepcao: 'receptionist',
  instrutor: 'instructor',
  consulta: 'read_only',
}

const SUGGESTABLE_ROLES: Exclude<UserRole, 'pendente'>[] = [
  'instrutor',
  'recepcao',
  'coordenador',
  'consulta',
]

interface FieldErrors {
  fullName?: string
  email?: string
  password?: string
  confirmPassword?: string
}

export function SignupPage() {
  usePageTitle('Pedir acesso')
  const { status } = useAuth()
  const formId = useId()
  const nameRef = useRef<HTMLInputElement>(null)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [requestedRole, setRequestedRole] = useState<Exclude<UserRole, 'pendente'>>('instrutor')

  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [sent, setSent] = useState(false)

  useEffect(() => {
    nameRef.current?.focus()
  }, [])

  if (!publicEnv || !supabase) {
    return (
      <FullScreenState
        title="Configuração indisponível"
        description="As variáveis públicas do frontend não foram definidas. Avise a equipe técnica antes de tentar pedir acesso."
      />
    )
  }

  if (status === 'signed-in') {
    return <Navigate to="/painel" replace />
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setFormError(null)

    const nextFieldErrors: FieldErrors = {}
    if (fullName.trim().length < 3) {
      nextFieldErrors.fullName = 'Informe seu nome completo.'
    }
    if (!email) {
      nextFieldErrors.email = 'Informe seu e-mail.'
    }
    if (password.length < 6) {
      nextFieldErrors.password = 'A senha precisa ter pelo menos 6 caracteres.'
    }
    if (confirmPassword !== password) {
      nextFieldErrors.confirmPassword = 'As senhas não são iguais.'
    }
    setFieldErrors(nextFieldErrors)
    if (Object.keys(nextFieldErrors).length > 0) return

    setSubmitting(true)
    const { error } = await supabase!.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName.trim(),
          requested_role: REQUESTED_ROLE_DB_VALUE[requestedRole],
        },
      },
    })
    setSubmitting(false)

    if (error) {
      setFormError(
        error.message.toLowerCase().includes('already registered')
          ? 'Já existe uma conta com esse e-mail.'
          : 'Não foi possível enviar seu pedido. Tente novamente.',
      )
      return
    }
    setSent(true)
  }

  if (sent) {
    return (
      <div className="relative flex min-h-screen bg-ink">
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
          <h2 className="font-display text-[1.75rem] font-semibold tracking-tight text-white">
            Pedido enviado
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-white/60">
            A coordenação do instituto vai analisar seu pedido de acesso como{' '}
            <strong className="text-white">{ROLE_LABELS[requestedRole]}</strong>. Você vai conseguir
            entrar assim que ela liberar sua conta.
          </p>
          <Link
            to="/entrar"
            className="mt-8 inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.12em] text-brand-green transition hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Voltar para o login
          </Link>
        </AuthPanel>
      </div>
    )
  }

  return (
    <div className="relative flex min-h-screen bg-ink">
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
        <Link
          to="/entrar"
          className="mb-8 inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.12em] text-white/45 transition hover:text-brand-green"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Voltar para o login
        </Link>
        <h2 className="font-display text-[1.75rem] font-semibold tracking-tight text-white">
          Pedir acesso
        </h2>
        <p className="mt-2 text-sm text-white/50">
          Preencha seus dados. A coordenação precisa aceitar seu pedido antes de você conseguir entrar.
        </p>

        <form id={formId} onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-5">
          <Input
            ref={nameRef}
            label="Nome completo"
            autoComplete="name"
            value={fullName}
            onChange={(event) => { setFullName(event.target.value); setFieldErrors((current) => ({ ...current, fullName: undefined })) }}
            error={fieldErrors.fullName}
            disabled={submitting}
            icon={<User className="h-4 w-4" aria-hidden="true" />}
          />

          <Input
            label="E-mail"
            type="email"
            autoComplete="email"
            spellCheck={false}
            autoCapitalize="none"
            value={email}
            onChange={(event) => { setEmail(event.target.value); setFieldErrors((current) => ({ ...current, email: undefined })) }}
            error={fieldErrors.email}
            disabled={submitting}
            icon={<Mail className="h-4 w-4" aria-hidden="true" />}
          />

          <div className="relative">
            <Input
              label="Senha"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password}
              onChange={(event) => { setPassword(event.target.value); setFieldErrors((current) => ({ ...current, password: undefined })) }}
              disabled={submitting}
              className="pr-12"
              icon={<Lock className="h-4 w-4" aria-hidden="true" />}
              error={fieldErrors.password}
              hint="Pelo menos 6 caracteres."
            />
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              className="absolute right-3 top-9 flex h-8 w-8 items-center justify-center rounded-md text-white/50 transition hover:text-white"
              aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
            >
              {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
            </button>
          </div>

          <Input
            label="Confirmar senha"
            type={showPassword ? 'text' : 'password'}
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => { setConfirmPassword(event.target.value); setFieldErrors((current) => ({ ...current, confirmPassword: undefined })) }}
            disabled={submitting}
            icon={<Lock className="h-4 w-4" aria-hidden="true" />}
            error={fieldErrors.confirmPassword}
          />

          <Select
            label="Papel que você acha que deveria ter"
            id={`${formId}-role`}
            value={requestedRole}
            onChange={(event) => setRequestedRole(event.target.value as Exclude<UserRole, 'pendente'>)}
            disabled={submitting}
            options={SUGGESTABLE_ROLES.map((value) => ({ value, label: ROLE_LABELS[value] }))}
          />
          <p className="-mt-3 text-xs text-white/35">
            A coordenação confirma ou troca esse papel ao aceitar seu pedido.
          </p>

          {formError && (
            <p role="alert" className="text-sm text-danger">
              {formError}
            </p>
          )}

          <Button type="submit" loading={submitting} className="mt-2 w-full">
            {submitting ? 'Enviando…' : 'Pedir acesso'}
          </Button>
        </form>

        <p className="mt-8 text-xs leading-relaxed text-white/35">
          Já tem conta?{' '}
          <Link to="/entrar" className="font-medium text-white/50 hover:text-brand-green">
            Entre por aqui
          </Link>
          .
        </p>
      </AuthPanel>
    </div>
  )
}
