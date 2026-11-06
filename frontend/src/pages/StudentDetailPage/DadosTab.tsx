import { User } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { changeStudentStatus, updateStudent } from '@/features/students/api'
import type { StudentDetail } from '@/entities/student/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'

export function DadosTab({ student, onChanged }: { student: StudentDetail; onChanged: () => void }) {
  const [fullName, setFullName] = useState(student.full_name)
  const [birthDate, setBirthDate] = useState(student.birth_date)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const [reason, setReason] = useState('')
  const [togglingStatus, setTogglingStatus] = useState(false)
  const [statusError, setStatusError] = useState<string | null>(null)

  async function handleSave(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      await updateStudent(student.id, {
        expected_updated_at: student.updated_at,
        full_name: fullName,
        birth_date: birthDate,
      })
      setSaved(true)
      onChanged()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleStatus() {
    if (reason.trim().length < 10) {
      setStatusError('Informe um motivo com pelo menos 10 caracteres.')
      return
    }
    setTogglingStatus(true)
    setStatusError(null)
    try {
      await changeStudentStatus(student.id, student.status === 'ativo' ? 'deactivate' : 'activate', {
        expected_updated_at: student.updated_at,
        reason,
      })
      setReason('')
      onChanged()
    } catch (caught) {
      setStatusError(friendlyMessage(caught))
    } finally {
      setTogglingStatus(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleSave} className="liquid-glass flex flex-col gap-4 rounded-2xl p-6">
        <Input
          label="Nome completo"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
          disabled={saving}
          icon={<User className="h-4 w-4" aria-hidden="true" />}
        />
        <Input
          label="Data de nascimento"
          type="date"
          value={birthDate}
          onChange={(event) => setBirthDate(event.target.value)}
          disabled={saving}
        />
        {error && <p className="text-sm text-danger">{error}</p>}
        {saved && <p className="text-sm text-brand-green">Dados atualizados.</p>}
        <Button type="submit" loading={saving} className="w-full sm:w-auto">
          {saving ? 'Salvando…' : 'Salvar alterações'}
        </Button>
      </form>

      <div className="liquid-glass flex flex-col gap-4 rounded-2xl p-6">
        <h2 className="font-display text-sm font-semibold text-white">
          {student.status === 'ativo' ? 'Desativar cadastro' : 'Reativar cadastro'}
        </h2>
        <p className="text-sm text-white/55">
          {student.status === 'ativo'
            ? 'Desativa sem excluir histórico. Exige um motivo registrado.'
            : 'Reativa o cadastro preservado, com os mesmos controles da desativação.'}
        </p>
        <Input
          label="Motivo"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          disabled={togglingStatus}
          hint="Entre 10 e 500 caracteres."
        />
        {statusError && <p className="text-sm text-danger">{statusError}</p>}
        <Button
          variant={student.status === 'ativo' ? 'danger' : 'primary'}
          loading={togglingStatus}
          onClick={handleToggleStatus}
          className="w-full sm:w-auto"
        >
          {student.status === 'ativo' ? 'Desativar estudante' : 'Reativar estudante'}
        </Button>
      </div>
    </div>
  )
}
