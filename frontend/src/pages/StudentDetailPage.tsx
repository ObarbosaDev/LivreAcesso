import { ArrowLeft, FileText, Mail, Phone, Plus, Printer, Star, User, UserMinus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  addGuardian,
  changeStudentStatus,
  getStudentDetail,
  listGuardians,
  setPrimaryGuardian,
  unlinkGuardian,
  updateStudent,
} from '@/features/students/api'
import type { StudentDetail } from '@/entities/student/types'
import { STUDENT_STATUS_LABELS } from '@/entities/student/types'
import type { GuardianListItem } from '@/entities/guardian/types'
import { GUARDIAN_RELATIONSHIPS, GUARDIAN_RELATIONSHIP_LABELS } from '@/entities/guardian/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { FullScreenState } from '@/shared/ui/FullScreenState'
import { Input } from '@/shared/ui/Input'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageFrame } from '@/shared/ui/PageFrame'

type Tab = 'dados' | 'responsaveis' | 'relatorio'

export function StudentDetailPage() {
  const { studentId } = useParams<{ studentId: string }>()
  const [student, setStudent] = useState<StudentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('dados')

  usePageTitle(student ? student.full_name : 'Estudante')

  const reload = useCallback(async () => {
    if (!studentId) return
    try {
      const detail = await getStudentDetail(studentId)
      setStudent(detail)
      setError(null)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setLoading(false)
    }
  }, [studentId])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca inicial ao entrar na tela ou trocar de estudante
    void reload()
  }, [reload])

  if (loading) {
    return <FullScreenState title="Carregando estudante" description="Só um instante." loading />
  }

  if (error || !student) {
    return (
      <div className="liquid-glass max-w-md rounded-2xl p-8 text-center">
        <p className="text-sm text-danger">{error ?? 'Estudante não encontrado.'}</p>
        <Link to="/estudantes" className="mt-4 inline-block text-sm text-brand-green">
          Voltar para estudantes
        </Link>
      </div>
    )
  }

  return (
    <PageFrame eyebrow="Prontuário operacional" title={student.full_name} description={`${student.age} anos · CPF ${student.cpf_masked}`}>
      <Link
        to="/estudantes"
        className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-white/50 transition hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Voltar para estudantes
      </Link>

      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="mt-1 text-sm text-white/55">
            {student.age} anos · CPF {student.cpf_masked}
          </p>
        </div>
        <StatusBadge
          label={STUDENT_STATUS_LABELS[student.status]}
          tone={student.status === 'ativo' ? 'success' : 'neutral'}
        />
      </div>

      <div className="mt-6 flex gap-1 border-b border-white/10">
        {(['dados', 'responsaveis', 'relatorio'] as const).map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            className={`px-4 py-2.5 text-sm font-medium transition ${
              tab === value
                ? 'border-b-2 border-brand-green text-white'
                : 'text-white/50 hover:text-white'
            }`}
          >
            {value === 'dados' ? 'Dados' : value === 'responsaveis' ? 'Responsáveis' : 'Relatório do aluno'}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === 'dados' ? (
          <DadosTab student={student} onChanged={reload} />
        ) : tab === 'responsaveis' ? (
          <ResponsaveisTab student={student} />
        ) : (
          <StudentReportTab student={student} />
        )}
      </div>
    </PageFrame>
  )
}

function DadosTab({ student, onChanged }: { student: StudentDetail; onChanged: () => void }) {
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

function StudentReportTab({ student }: { student: StudentDetail }) {
  return <div className="student-report space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-green">Acompanhamento individual</p><h2 className="mt-2 font-display text-2xl font-semibold text-white">Relatório de {student.full_name}</h2><p className="mt-2 text-sm text-white/45">Documento de acompanhamento para orientar a equipe e a família.</p></div><button type="button" onClick={() => window.print()} className="inline-flex items-center gap-2 border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:border-brand-green hover:text-brand-green"><Printer className="h-4 w-4" aria-hidden="true" /> Imprimir relatório</button></div>
    <div className="grid gap-4 md:grid-cols-3"><ReportFact label="Situação cadastral" value={STUDENT_STATUS_LABELS[student.status]} /><ReportFact label="Idade" value={`${student.age} anos`} /><ReportFact label="Responsável principal" value={student.guardian.full_name} /></div>
    <div className="grid gap-6 lg:grid-cols-2"><ReportSection title="Desenvolvimento" description="Registre avanços observados em autonomia, comunicação, interação e participação." /><ReportSection title="Desempenho" description="Acompanhamento de objetivos, atividades realizadas e evolução do estudante." /><ReportSection title="Apoios e acessibilidade" description="Informações importantes para oferecer uma experiência segura, inclusiva e adequada — especialmente em necessidades específicas como autismo." /><ReportSection title="Observações da equipe" description="Anotações relevantes para o próximo atendimento, reunião ou contato com a família." /></div>
    <div className="border border-dashed border-white/15 bg-white/[.02] p-5"><div className="flex items-center gap-3"><FileText className="h-5 w-5 text-brand-green" aria-hidden="true" /><div><p className="text-sm font-semibold text-white">Histórico de acompanhamento</p><p className="mt-1 text-sm text-white/45">Ainda não há registros de desenvolvimento para este estudante.</p></div></div><p className="mt-4 border-t border-white/10 pt-4 text-xs leading-5 text-white/35">A estrutura do relatório já está preparada. O lançamento de avaliações e observações será conectado ao módulo pedagógico.</p></div>
  </div>
}

function ReportFact({ label, value }: { label: string; value: string }) { return <div className="border border-white/10 bg-white/[.02] p-4"><p className="text-xs uppercase tracking-[0.12em] text-white/35">{label}</p><p className="mt-3 font-semibold text-white">{value}</p></div> }

function ReportSection({ title, description }: { title: string; description: string }) { return <section className="border border-white/10 p-5"><h3 className="font-display text-lg font-semibold text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-white/45">{description}</p><div className="mt-5 border border-dashed border-white/12 px-4 py-5 text-xs text-white/35">Nenhum registro lançado ainda.</div></section> }

function ResponsaveisTab({ student }: { student: StudentDetail }) {
  const [guardians, setGuardians] = useState<GuardianListItem[] | null>(null)
  const [studentUpdatedAt, setStudentUpdatedAt] = useState(student.updated_at)
  const [error, setError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)

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

  async function handleUnlink(guardianId: string) {
    const reason = window.prompt('Motivo da desvinculação (mínimo 10 caracteres):')
    if (!reason || reason.trim().length < 10) return
    try {
      await unlinkGuardian(student.id, guardianId, {
        expected_student_updated_at: studentUpdatedAt,
        reason,
      })
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
            <div className="mt-4 flex gap-2">
              {!guardian.is_primary && (
                <button
                  type="button"
                  onClick={() => handleSetPrimary(guardian.id)}
                  className="text-xs font-medium text-brand-green hover:text-brand-green-soft"
                >
                  Tornar principal
                </button>
              )}
              {!guardian.is_primary && (
                <button
                  type="button"
                  onClick={() => handleUnlink(guardian.id)}
                  className="flex items-center gap-1 text-xs font-medium text-danger/80 hover:text-danger"
                >
                  <UserMinus className="h-3 w-3" aria-hidden="true" />
                  Desvincular
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
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
      <div className="flex flex-col gap-2">
        <label htmlFor="relationship" className="text-sm font-medium text-white">
          Parentesco
        </label>
        <select
          id="relationship"
          value={relationship}
          onChange={(event) =>
            setRelationship(event.target.value as (typeof GUARDIAN_RELATIONSHIPS)[number])
          }
          className="h-12 rounded-xl border border-white/10 bg-white/5 px-4 text-white outline-none transition focus:border-brand-green focus:bg-white/8 focus:ring-4 focus:ring-brand-green/15"
        >
          {GUARDIAN_RELATIONSHIPS.map((value) => (
            <option key={value} value={value} className="bg-surface">
              {GUARDIAN_RELATIONSHIP_LABELS[value]}
            </option>
          ))}
        </select>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      <Button type="submit" loading={submitting} className="w-full sm:w-auto">
        {submitting ? 'Salvando…' : 'Adicionar responsável'}
      </Button>
    </form>
  )
}
