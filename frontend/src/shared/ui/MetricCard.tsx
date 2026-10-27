import type { LucideIcon } from 'lucide-react'

interface MetricCardProps { label: string; value: string | number; detail?: string; icon: LucideIcon; tone?: 'green' | 'amber' | 'blue' | 'red' }

const TONES = { green: 'text-brand-green bg-brand-green/12', amber: 'text-warning bg-warning/12', blue: 'text-sky-300 bg-sky-300/12', red: 'text-danger bg-danger/12' }

/** Métrica de operação: número grande, significado curto e cor sem depender só dela. */
export function MetricCard({ label, value, detail, icon: Icon, tone = 'green' }: MetricCardProps) {
  return <article className="liquid-glass rounded-3xl p-5"><div className="flex items-start justify-between gap-4"><span className={`flex h-10 w-10 items-center justify-center rounded-2xl ${TONES[tone]}`}><Icon className="h-5 w-5" aria-hidden="true" /></span>{detail && <span className="text-xs text-white/35">{detail}</span>}</div><p className="mt-7 text-sm text-white/50">{label}</p><p className="mt-1 font-display text-3xl font-semibold tracking-[-0.04em] text-white">{value}</p></article>
}
