import { Mail, Phone, Plus, Star, UserMinus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { addGuardian, listGuardians, setPrimaryGuardian, unlinkGuardian } from '@/features/students/api'
import type { StudentDetail } from '@/entities/student/types'
import type { GuardianListItem } from '@/entities/guardian/types'
import { GUARDIAN_RELATIONSHIPS, GUARDIAN_RELATIONSHIP_LABELS } from '@/entities/guardian/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'

export function ResponsaveisTab({ student }: { student: StudentDetail }) {
  const [guardians, setGuardians] = useState<GuardianListItem[] | null>(null)
  const [studentUpdatedAt, setStudentUpdatedAt] = useState(student.updated_at)
  const [error, setError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [unlinkingGuardianId, setUnlinkingGuardianId] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      const result = await listGuardians(student.id)
      setGuardians(result.items)
      setStudentUpdatedAt(result.student_updated_at)
      setError(null)
    } catch (caught) {
      setError(friendlyMessage(caught))
    }
  }, [student.id])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca inicial da lista ao abrir a aba
    void reload()
  }, [reload])

  async function handleSetPrimary(guardianId: string) {
    try {
      await setPrimaryGuardian(student.id, guardianId, studentUpdatedAt)
      await reload()
    } catch (caught) {
      setError(friendlyMessage(caught))
    }
  }

  if (error) return <p className="text-sm text-danger">{error}</p>
  if (!guardians) return <p className="text-sm text-white/50">Carregando responsáveis…</p>

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold text-white">
          {guardians.length} {guardians.length === 1 ? 'responsável' : 'responsáveis'}
        </h2>
        <Button variant="secondary" onClick={() => setShowAddForm((value) => !value)} className="gap-2">
          <Plus className="h-4 w-4" aria-hidden="true" />
          Adicionar
        </Button>
      </div>

      {showAddForm && (
        <AddGuardianForm
          studentId={student.id}
          studentUpdatedAt={studentUpdatedAt}
          onDone={() => {
            setShowAddForm(false)
            void reload()
          }}
        />
      )}

      <ul className="flex flex-col gap-3">
        {guardians.map((guardian) => (
          <li key={guardian.id} className="liquid-glass rounded-2xl p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="flex items-center gap-2 text-sm font-medium text-white">
                  {guardian.full_name}
                  {guardian.is_primary && (
                    <Star className="h-3.5 w-3.5 fill-warning text-warning" aria-hidden="true" />
                  )}
                </p>
                <p className="mt-1 text-xs text-white/50">
                  {GUARDIAN_RELATIONSHIP_LABELS[guardian.relationship]}
                </p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/55">
              <span className="flex items-center gap-1.5">
                <Phone className="h-3 w-3" aria-hidden="true" />
                {guardian.phone_masked}
              </span>
              {guardian.email_masked && (
                <span className="flex items-center gap-1.5">
                  <Mail className="h-3 w-3" aria-hidden="true" />
                  {guardian.email_masked}
                </span>
              )}
            </div>
            {!guardian.is_primary && (
              <div className="mt-4 flex gap-2">
                <Button type="button" size="sm" variant="primary" onClick={() => handleSetPrimary(guardian.id)}>
                  Tornar principal
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="danger"
                  onClick={() => setUnlinkingGuardianId(guardian.id)}
                >
                  <UserMinus className="h-3 w-3" aria-hidden="true" />
                  Desvincular
                </Button>
              </div>
            )}
            {unlinkingGuardianId === guardian.id && (
              <UnlinkGuardianForm
                studentId={student.id}
                guardianId={guardian.id}
                studentUpdatedAt={studentUpdatedAt}
                onCancel={() => setUnlinkingGuardianId(null)}
                onDone={() => {
                  setUnlinkingGuardianId(null)
                  void reload()
                }}
              />
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function UnlinkGuardianForm({
  studentId,
  guardianId,
  studentUpdatedAt,
  onCancel,
  onDone,
}: {
  studentId: string
  guardianId: string
  studentUpdatedAt: string
  onCancel: () => void
  onDone: () => void
}) {
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (reason.trim().length < 10) {
      setError('Informe um motivo com pelo menos 10 caracteres.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await unlinkGuardian(studentId, guardianId, {
        expected_student_updated_at: studentUpdatedAt,
        reason,
      })
      onDone()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 border-t border-white/10 pt-4">
      <Input
        label="Motivo da desvinculação"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        disabled={submitting}
        hint="Pelo menos 10 caracteres."
      />
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" variant="danger" loading={submitting}>
          Confirmar desvinculação
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}

function AddGuardianForm({
  studentId,
  studentUpdatedAt,
  onDone,
}: {
  studentId: string
  studentUpdatedAt: string
  onDone: () => void
}) {
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [relationship, setRelationship] = useState<(typeof GUARDIAN_RELATIONSHIPS)[number]>(
    'contato_responsavel',
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await addGuardian(studentId, {
        expected_student_updated_at: studentUpdatedAt,
        relationship,
        receives_communications: true,
        make_primary: false,
        guardian: { full_name: fullName, phone, email: email || undefined },
      })
      onDone()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="liquid-glass flex flex-col gap-4 rounded-2xl p-5">
      <Input label="Nome completo" value={fullName} onChange={(e) => setFullName(e.target.value)} />
      <Input label="Telefone" value={phone} onChange={(e) => setPhone(e.target.value)} />
      <Input
        label="E-mail (opcional)"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <Select
        label="Parentesco"
        id="relationship"
        value={relationship}
        onChange={(event) =>
          setRelationship(event.target.value as (typeof GUARDIAN_RELATIONSHIPS)[number])
        }
        options={GUARDIAN_RELATIONSHIPS.map((value) => ({
          value,
          label: GUARDIAN_RELATIONSHIP_LABELS[value],
        }))}
      />
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" loading={submitting} className="w-full sm:w-auto">
        {submitting ? 'Salvando…' : 'Adicionar responsável'}
      </Button>
    </form>
  )
}
