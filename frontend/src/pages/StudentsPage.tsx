import { ArrowUpRight, Loader2, Search, SlidersHorizontal, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { listStudents } from '@/features/students/api'
import { listModalities } from '@/features/classes/api'
import type { Student, StudentStatus } from '@/entities/student/types'
import { STUDENT_STATUS_LABELS } from '@/entities/student/types'
import type { Modality, Unit } from '@/entities/class/types'
import { UNIT_LABELS, UNITS } from '@/entities/class/types'
import { ApiError, friendlyMessage } from '@/shared/api/problemDetails'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Input } from '@/shared/ui/Input'
import { MetricCard } from '@/shared/ui/MetricCard'
import { PageFrame } from '@/shared/ui/PageFrame'
import { Select } from '@/shared/ui/Select'
import { StatusBadge } from '@/shared/ui/StatusBadge'

const PAGE_SIZE = 25

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR').format(new Date(iso))
}

export function StudentsPage() {
  usePageTitle('Estudantes')
  const navigate = useNavigate()
  const { profile } = useAuth()
  const canRegisterStudents = profile?.capabilities.includes('students:create') ?? false

  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query)
  const [status, setStatus] = useState<StudentStatus | ''>('')
  const [unit, setUnit] = useState<Unit | ''>('')
  const [modalityId, setModalityId] = useState('')
  const [modalities, setModalities] = useState<Modality[]>([])
  const [page, setPage] = useState(1)

  const [data, setData] = useState<{ items: Student[]; total: number; totalPages: number } | null>(
    null,
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listModalities(true).then((result) => setModalities(result.items)).catch(() => {})
  }, [])

  // Volta para a página 1 quando o filtro muda. Comparado durante a própria
  // renderização (o padrão oficial do React para "ajustar estado quando uma
  // prop muda"), em vez de um efeito, para não gastar um ciclo extra de
  // renderização só para resetar um número de página.
  const [appliedFilters, setAppliedFilters] = useState({ debouncedQuery, status, unit, modalityId })
  if (
    appliedFilters.debouncedQuery !== debouncedQuery ||
    appliedFilters.status !== status ||
    appliedFilters.unit !== unit ||
    appliedFilters.modalityId !== modalityId
  ) {
    setAppliedFilters({ debouncedQuery, status, unit, modalityId })
    if (page !== 1) setPage(1)
  }

  useEffect(() => {
    const controller = new AbortController()
    // setLoading/setError síncronos no início do efeito são o padrão usual
    // de busca de dados: o efeito sincroniza com uma API externa, e o
    // carregamento precisa ficar visível antes da resposta chegar.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)

    listStudents({
      status: status || undefined,
      unit: unit || undefined,
      modalityId: modalityId || undefined,
      query: debouncedQuery.trim().length >= 2 ? debouncedQuery.trim() : undefined,
      page,
      pageSize: PAGE_SIZE,
      signal: controller.signal,
    })
      .then((result) => {
        setData({ items: result.items, total: result.total, totalPages: result.total_pages })
      })
      .catch((caught: unknown) => {
        if (caught instanceof ApiError || (caught as Error)?.name !== 'AbortError') {
          setError(friendlyMessage(caught))
        }
      })
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [debouncedQuery, status, unit, modalityId, page])

  return (
    <PageFrame
      eyebrow="Cadastro e acompanhamento"
      title="Estudantes"
      description="Pessoas atendidas pelo instituto e seus responsáveis."
      actions={
        canRegisterStudents && (
          <Link
            to="/estudantes/novo"
            className="group inline-flex h-11 items-center justify-center gap-2 border border-brand-green bg-brand-green px-5 text-sm font-semibold text-ink transition hover:bg-brand-green-soft"
          >
            Novo estudante <ArrowUpRight className="h-4 w-4 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
          </Link>
        )
      }
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCard label="Total cadastrado" value={data?.total ?? '—'} icon={Users} />
        <MetricCard
          label="Filtro atual"
          value={status ? STUDENT_STATUS_LABELS[status] : 'Todos os status'}
          icon={SlidersHorizontal}
          tone="blue"
        />
        <MetricCard
          label="Exibidos nesta página"
          value={data ? `${data.items.length} de ${data.total}` : '—'}
          icon={Search}
          tone="amber"
        />
      </div>

      <div className="liquid-glass mt-6 flex flex-col gap-4 border-t-2 border-t-brand-green/50 p-4 sm:flex-row sm:items-end">
        <Input
          label="Pesquisar"
          placeholder="Buscar por nome…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          icon={<Search className="h-4 w-4" aria-hidden="true" />}
          className="sm:max-w-md"
        />
        <div className="sm:w-44">
          <Select
            label="Status"
            value={status}
            onChange={(event) => setStatus(event.target.value as StudentStatus | '')}
            options={[
              { value: '', label: 'Todos' },
              { value: 'ativo', label: 'Ativo' },
              { value: 'inativo', label: 'Inativo' },
            ]}
          />
        </div>
        <div className="sm:w-44">
          <Select
            label="Unidade"
            value={unit}
            onChange={(event) => setUnit(event.target.value as Unit | '')}
            options={[
              { value: '', label: 'Todas as unidades' },
              ...UNITS.map((value) => ({ value, label: UNIT_LABELS[value] })),
            ]}
          />
        </div>
        <div className="sm:w-48">
          <Select
            label="Modalidade"
            value={modalityId}
            onChange={(event) => setModalityId(event.target.value)}
            options={[
              { value: '', label: 'Todas as modalidades' },
              ...modalities.map((modality) => ({ value: modality.id, label: modality.name })),
            ]}
          />
        </div>
        <div className="hidden items-center gap-2 pb-3 text-xs text-white/35 sm:flex"><SlidersHorizontal className="h-4 w-4" aria-hidden="true" /> Filtros aplicados automaticamente</div>
      </div>

      <div className="@container mt-6">
        {loading && !data && (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Carregando estudantes…
          </div>
        )}

        {error && (
            <div className="liquid-glass border-l-2 border-l-danger p-8 text-center">
            <p className="text-sm text-danger">{error}</p>
          </div>
        )}

        {!loading && !error && data && data.items.length === 0 && (
          <EmptyState
            icon={Users}
            title={debouncedQuery || status || unit || modalityId ? 'Nenhum estudante encontrado' : 'Ainda não há estudantes cadastrados'}
            description={
              debouncedQuery || status || unit || modalityId
                ? 'Tente outro termo ou limpe o filtro para ver todos os estudantes.'
                : 'Cadastre o primeiro estudante para começar a organizar turmas e presença.'
            }
            action={
              !debouncedQuery && !status && !unit && !modalityId && canRegisterStudents && (
                <Link
                  to="/estudantes/novo"
                  className="inline-flex items-center gap-2 border border-brand-green bg-brand-green px-4 py-2.5 text-sm font-semibold text-ink"
                >
                  Cadastrar primeiro estudante <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              )
            }
          />
        )}

        {!error && data && data.items.length > 0 && (
          <>
            {/* Tabela em telas largas o bastante; vira cartões quando o espaço aperta — a medida é do container, não da janela, porque esta área divide espaço com o menu lateral. */}
            <table className="hidden w-full text-left text-sm @2xl:table">
              <thead>
                <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.16em] text-white/35">
                  <th className="px-4 py-4 font-medium">Estudante</th>
                  <th className="py-4 font-medium">Status</th>
                  <th className="py-4 font-medium">Responsável</th>
                  <th className="py-4 font-medium">Cadastro</th>
                  <th className="py-4 pr-4" />
                </tr>
              </thead>
              <tbody>
                {data.items.map((student) => (
                  <tr
                    key={student.id}
                    onClick={() => navigate(`/estudantes/${student.id}`)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        navigate(`/estudantes/${student.id}`)
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label={`Ver detalhes de ${student.full_name}`}
                    className="group cursor-pointer border-b border-white/5 transition hover:bg-white/[.045] focus:outline-none focus:ring-2 focus:ring-inset focus:ring-brand-green"
                  >
                    <td className="px-4 py-4"><span className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-green/15 text-sm font-bold text-brand-green">{student.full_name.slice(0, 1).toUpperCase()}</span><span><span className="block font-semibold text-white">{student.full_name}</span><span className="block text-xs text-white/35">{student.cpf_masked}</span></span></span></td>
                    <td className="py-4"><StatusBadge
                      label={STUDENT_STATUS_LABELS[student.status]}
                      tone={student.status === 'ativo' ? 'success' : 'neutral'}
                    /></td>
                    <td className="py-4 text-white/60">{student.guardian_name ?? '—'}</td>
                    <td className="py-4 text-white/60">{formatDate(student.created_at)}</td>
                    <td className="py-4 pr-4 text-right"><ArrowUpRight className="ml-auto h-4 w-4 text-white/20 transition group-hover:text-brand-green" aria-hidden="true" /></td>
                  </tr>
                ))}
              </tbody>
            </table>

            <ul className="flex flex-col gap-3 @2xl:hidden">
              {data.items.map((student) => (
                <li key={student.id}>
                  <Link
                    to={`/estudantes/${student.id}`}
                    className="liquid-glass block border-l-2 border-l-white/15 p-4 transition hover:border-l-brand-green"
                  >
                  <div className="flex items-start justify-between gap-3">
                    <span className="font-medium text-white">{student.full_name}</span>
                    <StatusBadge
                      label={STUDENT_STATUS_LABELS[student.status]}
                      tone={student.status === 'ativo' ? 'success' : 'neutral'}
                    />
                  </div>
                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-white/50">
                    <div>
                      <dt>Responsável</dt>
                      <dd className="text-white/75">{student.guardian_name ?? '—'}</dd>
                    </div>
                    <div>
                      <dt>Cadastro</dt>
                      <dd className="text-white/75">{formatDate(student.created_at)}</dd>
                    </div>
                  </dl>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}

        {data && data.totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between text-sm text-white/55">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
              className="rounded-lg px-3 py-1.5 transition hover:bg-white/8 disabled:pointer-events-none disabled:opacity-30"
            >
              Anterior
            </button>
            <span>
              Página {page} de {data.totalPages}
            </span>
            <button
              type="button"
              disabled={page >= data.totalPages}
              onClick={() => setPage((value) => value + 1)}
              className="rounded-lg px-3 py-1.5 transition hover:bg-white/8 disabled:pointer-events-none disabled:opacity-30"
            >
              Próxima
            </button>
          </div>
        )}
      </div>
    </PageFrame>
  )
}
