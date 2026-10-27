import { ArrowLeft, Mail, Phone, User } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { registerStudent } from '@/features/students/api'
import { ApiError, friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

interface FieldErrors {
  [field: string]: string
}

/**
 * Cadastro cria a pessoa e o responsável principal numa só operação — a
 * matrícula em turma é um fluxo separado, só depois que Turmas existir.
 */
export function NewStudentPage() {
  usePageTitle('Novo estudante')
  const navigate = useNavigate()

  const [fullName, setFullName] = useState('')
  const [cpf, setCpf] = useState('')
  const [birthDate, setBirthDate] = useState('')
  const [guardianName, setGuardianName] = useState('')
  const [guardianPhone, setGuardianPhone] = useState('')
  const [guardianEmail, setGuardianEmail] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setFormError(null)
    setFieldErrors({})
    setSubmitting(true)

    try {
      await registerStudent({
        full_name: fullName,
        cpf,
        birth_date: birthDate,
        guardian: {
          full_name: guardianName,
          phone: guardianPhone,
          email: guardianEmail || undefined,
        },
      })
      navigate('/estudantes')
    } catch (caught) {
      if (caught instanceof ApiError && caught.fieldErrors.length > 0) {
        const nextErrors: FieldErrors = {}
        for (const fieldError of caught.fieldErrors) {
          nextErrors[fieldError.field] = fieldError.message
        }
        setFieldErrors(nextErrors)
      }
      setFormError(friendlyMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-xl">
      <Link
        to="/estudantes"
        className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-white/50 transition hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Voltar para estudantes
      </Link>

      <h1 className="font-display text-2xl font-semibold text-white">Cadastrar estudante</h1>
      <p className="mt-2 text-sm text-white/55">
        Cria o cadastro pessoal e o responsável principal. A matrícula em uma turma é feita depois,
        em um passo separado.
      </p>

      <form onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-8">
        <fieldset className="liquid-glass flex flex-col gap-5 rounded-2xl p-6">
          <legend className="px-1 font-display text-sm font-semibold text-white">
            Dados do estudante
          </legend>
          <Input
            label="Nome completo"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            disabled={submitting}
            error={fieldErrors.full_name}
            icon={<User className="h-4 w-4" aria-hidden="true" />}
          />
          <Input
            label="CPF"
            placeholder="000.000.000-00"
            value={cpf}
            onChange={(event) => setCpf(event.target.value)}
            disabled={submitting}
            error={fieldErrors.cpf}
            hint="Com ou sem pontuação."
          />
          <Input
            label="Data de nascimento"
            type="date"
            value={birthDate}
            onChange={(event) => setBirthDate(event.target.value)}
            disabled={submitting}
            error={fieldErrors.birth_date}
          />
        </fieldset>

        <fieldset className="liquid-glass flex flex-col gap-5 rounded-2xl p-6">
          <legend className="px-1 font-display text-sm font-semibold text-white">Responsável</legend>
          <Input
            label="Nome completo"
            value={guardianName}
            onChange={(event) => setGuardianName(event.target.value)}
            disabled={submitting}
            error={fieldErrors['guardian.full_name']}
            icon={<User className="h-4 w-4" aria-hidden="true" />}
          />
          <Input
            label="Telefone"
            placeholder="(61) 90000-0000"
            value={guardianPhone}
            onChange={(event) => setGuardianPhone(event.target.value)}
            disabled={submitting}
            error={fieldErrors['guardian.phone']}
            icon={<Phone className="h-4 w-4" aria-hidden="true" />}
          />
          <Input
            label="E-mail (opcional)"
            type="email"
            value={guardianEmail}
            onChange={(event) => setGuardianEmail(event.target.value)}
            disabled={submitting}
            error={fieldErrors['guardian.email']}
            icon={<Mail className="h-4 w-4" aria-hidden="true" />}
          />
        </fieldset>

        {formError && (
          <p role="alert" className="text-sm text-danger">
            {formError}
          </p>
        )}

        <Button type="submit" loading={submitting} className="w-full sm:w-auto">
          {submitting ? 'Salvando…' : 'Cadastrar estudante'}
        </Button>
      </form>
    </div>
  )
}
