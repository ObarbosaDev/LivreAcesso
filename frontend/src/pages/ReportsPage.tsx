import { BarChart3, Download, FileText, Printer, UsersRound } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { getClassOccupancy, listClasses } from '@/features/classes/api'
import { listStudents } from '@/features/students/api'
import type { SchoolClass } from '@/entities/class/types'
import type { Student } from '@/entities/student/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { EmptyState } from '@/shared/ui/EmptyState'
import { MetricCard } from '@/shared/ui/MetricCard'
import { PageFrame } from '@/shared/ui/PageFrame'

interface Occupancy { classId: string; capacity: number; enrolled: number }

export function ReportsPage() {
  usePageTitle('Relatórios')
  const [students, setStudents] = useState<Student[]>([])
  const [classes, setClasses] = useState<SchoolClass[]>([])
  const [occupancies, setOccupancies] = useState<Occupancy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      listStudents({ page: 1, pageSize: 100, signal: controller.signal }),
      listClasses({ active: true, page: 1, pageSize: 100, signal: controller.signal }),
    ]).then(async ([studentPage, classPage]) => {
      setStudents(studentPage.items); setClasses(classPage.items)
      const rows = await Promise.all(classPage.items.map(async (item) => { const result = await getClassOccupancy(item.id, controller.signal).catch(() => ({ capacity: item.capacity, enrolled: 0 })); return { classId: item.id, capacity: result.capacity, enrolled: result.enrolled } }))
      setOccupancies(rows)
    }).catch((caught: unknown) => { if ((caught as Error)?.name !== 'AbortError') setError(friendlyMessage(caught)) }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [])

  const activeStudents = students.filter((item) => item.status === 'ativo').length
  const inactiveStudents = students.filter((item) => item.status === 'inativo').length
  const capacity = occupancies.reduce((sum, item) => sum + item.capacity, 0)
  const enrolled = occupancies.reduce((sum, item) => sum + item.enrolled, 0)
  const occupancyRate = capacity ? Math.round((enrolled / capacity) * 100) : 0
  const reportRows = useMemo(() => classes.map((item) => { const occupancy = occupancies.find((entry) => entry.classId === item.id); return { name: item.name, location: item.location, enrolled: occupancy?.enrolled ?? 0, capacity: occupancy?.capacity ?? item.capacity, rate: occupancy?.capacity ? Math.round(((occupancy.enrolled ?? 0) / occupancy.capacity) * 100) : 0 } }), [classes, occupancies])

  function downloadCsv() {
    const header = 'Turma,Local,Matriculados,Capacidade,Ocupação (%)'
    const body = reportRows.map((row) => [row.name, row.location, row.enrolled, row.capacity, row.rate].map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n')
    const blob = new Blob([`${header}\n${body}`], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'relatorio-operacional.csv'; anchor.click(); URL.revokeObjectURL(url)
  }

  return <div className="report-page"><PageFrame eyebrow="Leitura da operação" title="Relatórios" description="Acompanhe os números que orientam decisões de cadastro, capacidade e atendimento." actions={<><Button variant="secondary" onClick={() => window.print()} disabled={loading}><Printer className="h-4 w-4" aria-hidden="true" /> Imprimir / PDF</Button><Button variant="secondary" onClick={downloadCsv} disabled={loading || reportRows.length === 0}><Download className="h-4 w-4" aria-hidden="true" /> Exportar CSV</Button></>}>
    {error && <div className="border border-danger/40 bg-danger/10 p-4 text-sm text-danger" role="alert">{error}</div>}
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><MetricCard label="Estudantes ativos" value={loading ? '—' : activeStudents} icon={UsersRound} /><MetricCard label="Estudantes inativos" value={loading ? '—' : inactiveStudents} icon={UsersRound} tone="amber" /><MetricCard label="Turmas ativas" value={loading ? '—' : classes.length} icon={BarChart3} tone="blue" /><MetricCard label="Ocupação geral" value={loading ? '—' : `${occupancyRate}%`} icon={BarChart3} tone="green" /></div>
    <section className="liquid-glass mt-6 p-6"><div className="flex items-center gap-3 border-b border-white/10 pb-5"><FileText className="h-5 w-5 text-brand-green" aria-hidden="true" /><div><h2 className="font-display text-xl font-semibold text-white">Ocupação por turma</h2><p className="mt-1 text-sm text-white/45">Capacidade registrada e matrículas ativas no momento da consulta.</p></div></div>{!loading && reportRows.length === 0 ? <div className="pt-6"><EmptyState icon={FileText} title="Ainda não há dados para reportar" description="Cadastre estudantes e turmas para gerar a primeira leitura operacional." /></div> : <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><thead><tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.14em] text-white/35"><th className="px-3 py-3">Turma</th><th className="py-3">Local</th><th className="py-3">Matrículas</th><th className="py-3">Capacidade</th><th className="py-3 pr-3">Ocupação</th></tr></thead><tbody>{reportRows.map((row) => <tr key={row.name} className="border-b border-white/8"><td className="px-3 py-4 font-semibold text-white">{row.name}</td><td className="py-4 text-white/55">{row.location}</td><td className="py-4 text-white">{row.enrolled}</td><td className="py-4 text-white/55">{row.capacity}</td><td className="py-4 pr-3"><div className="flex items-center gap-3"><span className="h-1.5 w-24 bg-white/10"><span className="block h-full bg-brand-green" style={{ width: `${Math.min(row.rate, 100)}%` }} /></span><span className="text-xs text-white/55">{row.rate}%</span></div></td></tr>)}</tbody></table></div>}</section>
  </PageFrame></div>
}
