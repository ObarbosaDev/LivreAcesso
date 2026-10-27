import { ArrowUpRight, CalendarDays, Loader2, MapPin, Search, Users as UsersIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { getClassOccupancy, listClasses } from '@/features/classes/api'
import type { SchoolClass } from '@/entities/class/types'
import { WEEKDAY_LABELS } from '@/entities/class/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Input } from '@/shared/ui/Input'
import { OccupancyBar } from '@/shared/ui/OccupancyBar'
import { EmptyState } from '@/shared/ui/EmptyState'
import { MetricCard } from '@/shared/ui/MetricCard'
import { PageFrame } from '@/shared/ui/PageFrame'
import { StatusBadge } from '@/shared/ui/StatusBadge'

const PAGE_SIZE = 25

export function ClassesPage() {
  usePageTitle('Turmas')

  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query)
  const [page, setPage] = useState(1)

  const [data, setData] = useState<{ items: SchoolClass[]; total: number; totalPages: number } | null>(
    null,
  )
  const [occupancy, setOccupancy] = useState<Record<string, { capacity: number; enrolled: number }>>(
    {},
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [appliedQuery, setAppliedQuery] = useState(debouncedQuery)
  if (appliedQuery !== debouncedQuery) {
    setAppliedQuery(debouncedQuery)
    if (page !== 1) setPage(1)
  }

  useEffect(() => {
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError(null)

    listClasses({
      active: true,
      query: debouncedQuery.trim().length >= 2 ? debouncedQuery.trim() : undefined,
      page,
      pageSize: PAGE_SIZE,
      signal: controller.signal,
    })
      .then((result) => {
        setData({ items: result.items, total: result.total, totalPages: result.total_pages })
        Promise.all(
          result.items.map((item) =>
            getClassOccupancy(item.id, controller.signal)
              .then((occ) => [item.id, { capacity: occ.capacity, enrolled: occ.enrolled }] as const)
              .catch(() => [item.id, { capacity: item.capacity, enrolled: 0 }] as const),
          ),
        ).then((pairs) => setOccupancy(Object.fromEntries(pairs)))
      })
      .catch((caught: unknown) => {
        if ((caught as Error)?.name !== 'AbortError') {
          setError(friendlyMessage(caught))
        }
      })
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [debouncedQuery, page])

  return (
    <PageFrame eyebrow="Programação e capacidade" title="Turmas" description="Organize horários, instrutores e ocupação sem perder a visão do todo." actions={<Link to="/turmas/nova" className="group inline-flex h-11 items-center gap-2 rounded-full bg-brand-green px-5 text-sm font-semibold text-ink transition hover:-translate-y-0.5 hover:bg-brand-green-soft">Nova turma <ArrowUpRight className="h-4 w-4" aria-hidden="true" /></Link>}>
      <div className="grid gap-4 md:grid-cols-3"><MetricCard label="Turmas ativas" value={data?.total ?? '—'} icon={CalendarDays} /><MetricCard label="Capacidade cadastrada" value={data ? Object.values(occupancy).reduce((sum, item) => sum + item.capacity, 0) : '—'} icon={UsersIcon} tone="amber" /><MetricCard label="Vagas ocupadas" value={data ? Object.values(occupancy).reduce((sum, item) => sum + item.enrolled, 0) : '—'} icon={UsersIcon} tone="blue" /></div>
      <div className="liquid-glass mt-6 rounded-3xl p-4"><Input
        label="Pesquisar"
        placeholder="Buscar por nome da turma…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        icon={<Search className="h-4 w-4" aria-hidden="true" />}
        className="max-w-md"
      /></div>

      <div className="mt-6">
        {loading && !data && (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Carregando turmas…
          </div>
        )}

        {error && (
          <div className="liquid-glass rounded-2xl p-8 text-center">
            <p className="text-sm text-danger">{error}</p>
          </div>
        )}

        {!loading && !error && data && data.items.length === 0 && (
          <EmptyState icon={UsersIcon} title={debouncedQuery ? 'Nenhuma turma encontrada' : 'A programação ainda está vazia'} description={debouncedQuery ? 'Tente outro termo ou limpe a busca para ver todas as turmas.' : 'Crie a primeira turma para começar a organizar horários, instrutores e matrículas.'} action={!debouncedQuery && <Link to="/turmas/nova" className="inline-flex items-center gap-2 rounded-full bg-brand-green px-4 py-2.5 text-sm font-semibold text-ink">Criar primeira turma <ArrowUpRight className="h-4 w-4" aria-hidden="true" /></Link>} />
        )}

        {!error && data && data.items.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((schoolClass) => {
              const occ = occupancy[schoolClass.id]
              return (
                  <div key={schoolClass.id} className="liquid-glass group flex flex-col gap-4 rounded-3xl p-5 transition hover:-translate-y-1 hover:border-brand-green/25">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="font-display text-base font-semibold text-white">
                      {schoolClass.name}
                    </h2>
                    <StatusBadge label="Ativa" tone="success" />
                  </div>

                  <p className="flex items-center gap-1.5 text-xs text-white/55">
                    <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                    {schoolClass.location}
                  </p>

                  <ul className="flex flex-col gap-1 text-xs text-white/55">
                    {schoolClass.schedules.map((schedule, index) => (
                      <li key={index}>
                        {WEEKDAY_LABELS[schedule.weekday]} · {schedule.starts_at.slice(0, 5)}–
                        {schedule.ends_at.slice(0, 5)}
                      </li>
                    ))}
                  </ul>

                  {schoolClass.instructors.length > 0 && (
                    <p className="text-xs text-white/40">
                      Instrutor{schoolClass.instructors.length > 1 ? 'es' : ''}:{' '}
                      {schoolClass.instructors.map((instructor) => instructor.full_name).join(', ')}
                    </p>
                  )}

                  <OccupancyBar
                    capacity={occ?.capacity ?? schoolClass.capacity}
                    enrolled={occ?.enrolled ?? 0}
                  />
                </div>
              )
            })}
          </div>
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
