import { ArrowLeft } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getStudentDetail } from '@/features/students/api'
import type { StudentDetail } from '@/entities/student/types'
import { STUDENT_STATUS_LABELS } from '@/entities/student/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { FullScreenState } from '@/shared/ui/FullScreenState'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageFrame } from '@/shared/ui/PageFrame'

import { DadosTab } from './DadosTab'
import { ResponsaveisTab } from './ResponsaveisTab'
import { StudentEvaluationReport } from './StudentEvaluationReport'

type Tab = 'dados' | 'responsaveis' | 'relatorio'

const TAB_LABELS: Record<Tab, string> = {
  dados: 'Dados',
  responsaveis: 'Responsáveis',
  relatorio: 'Relatório do aluno',
}

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
    <PageFrame
      eyebrow="Prontuário operacional"
      title={student.full_name}
      description={`${student.age} anos · CPF ${student.cpf_masked}`}
    >
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
        {(Object.keys(TAB_LABELS) as Tab[]).map((value) => (
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
            {TAB_LABELS[value]}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === 'dados' ? (
          <DadosTab student={student} onChanged={reload} />
        ) : tab === 'responsaveis' ? (
          <ResponsaveisTab student={student} />
        ) : (
          <StudentEvaluationReport student={student} />
        )}
      </div>
    </PageFrame>
  )
}
