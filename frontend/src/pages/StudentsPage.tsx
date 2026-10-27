import { ArrowUpRight, Loader2, Search, SlidersHorizontal, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { listStudents } from '@/features/students/api'
import type { Student, StudentStatus } from '@/entities/student/types'
import { STUDENT_STATUS_LABELS } from '@/entities/student/types'
import { ApiError, friendlyMessage } from '@/shared/api/problemDetails'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Input } from '@/shared/ui/Input'
import { StatusBadge } from '@/shared/ui/StatusBadge'

const PAGE_SIZE = 25

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR').format(new Date(iso))
}

export function StudentsPage() {
  usePageTitle('Estudantes')
  const navigate = useNavigate()

  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query)
  const [status, setStatus] = useState<StudentStatus | ''>('')
  const [page, setPage] = useState(1)

  const [data, setData] = useState<{ items: Student[]; total: number; totalPages: number } | null>(
    null,
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Volta para a página 1 quando o filtro muda. Comparado durante a própria
  // renderização (o padrão oficial do React para "ajustar estado quando uma
  // prop muda"), em vez de um efeito, para não gastar um ciclo extra de
  // renderização só para resetar um número de página.
  const [appliedFilters, setAppliedFilters] = useState({ debouncedQuery, status })
  if (appliedFilters.debouncedQuery !== debouncedQuery || appliedFilters.status !== status) {
    setAppliedFilters({ debouncedQuery, status })
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
  }, [debouncedQuery, status, page])

  return (
    <div className="page-enter mx-auto max-w-[1400px] pb-12">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-green">Cadastro e acompanhamento</p>
          <h1 className="mt-2 font-display text-4xl font-semibold tracking-[-0.04em] text-white">Estudantes</h1>
          <p className="mt-2 text-sm text-white/50">Pessoas atendidas pelo instituto e seus responsáveis.</p>
        </div>
        <Link
          to="/estudantes/novo"
          className="group inline-flex h-11 items-center justify-center gap-2 rounded-full bg-brand-green px-5 text-sm font-semibold text-ink transition hover:-translate-y-px hover:bg-brand-green-soft"
        >
          Novo estudante <ArrowUpRight className="h-4 w-4 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
        </Link>
      </div>

      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        <div className="liquid-glass rounded-2xl px-4 py-3"><p className="text-xs text-white/40">Total cadastrado</p><p className="mt-1 font-display text-2xl font-semibold text-white">{data?.total ?? '—'}</p></div>
        <div className="liquid-glass rounded-2xl px-4 py-3"><p className="text-xs text-white/40">Filtro atual</p><p className="mt-1 text-sm font-semibold text-white">{status ? STUDENT_STATUS_LABELS[status] : 'Todos os status'}</p></div>
        <div className="liquid-glass rounded-2xl px-4 py-3"><p className="text-xs text-white/40">Exibidos nesta página</p><p className="mt-1 text-sm font-semibold text-white">{data?.items.length ?? '—'} de {data?.total ?? '—'}</p></div>
      </div>

      <div className="liquid-glass mt-6 flex flex-col gap-4 rounded-3xl p-4 sm:flex-row sm:items-end">
        <Input
          label="Pesquisar"
          placeholder="Buscar por nome…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          icon={<Search className="h-4 w-4" aria-hidden="true" />}
          className="sm:max-w-md"
        />
        <div className="flex flex-col gap-2 sm:w-44">
          <label htmlFor="status-filter" className="text-sm font-medium text-white">
            Status
          </label>
          <select
            id="status-filter"
            value={status}
            onChange={(event) => setStatus(event.target.value as StudentStatus | '')}
            className="h-12 rounded-xl border border-white/10 bg-white/5 px-4 text-white outline-none transition focus:border-brand-green focus:bg-white/8 focus:ring-4 focus:ring-brand-green/15"
          >
            <option value="" className="bg-surface">
              Todos
            </option>
            <option value="ativo" className="bg-surface">
              Ativo
            </option>
            <option value="inativo" className="bg-surface">
              Inativo
            </option>
          </select>
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
          <div className="liquid-glass rounded-2xl p-8 text-center">
            <p className="text-sm text-danger">{error}</p>
          </div>
        )}

        {!loading && !error && data && data.items.length === 0 && (
          <div className="liquid-glass flex flex-col items-center gap-3 rounded-2xl p-12 text-center">
            <Users className="h-6 w-6 text-white/40" aria-hidden="true" />
            <p className="text-sm text-white/55">
              {debouncedQuery || status
                ? 'Nenhum estudante encontrado para este filtro.'
                : 'Ainda não existem estudantes cadastrados.'}
            </p>
          </div>
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
                    className="group cursor-pointer border-b border-white/5 transition hover:bg-white/[.045]"
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
                    className="liquid-glass block rounded-2xl p-4 transition hover:border-brand-green/30"
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
    </div>
  )
}
