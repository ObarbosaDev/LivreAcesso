import type { LucideIcon } from 'lucide-react'

interface MetricCardProps { label: string; value: string | number; detail?: string; icon: LucideIcon; tone?: 'green' | 'amber' | 'blue' | 'red' }

const TONES = { green: 'border-l-brand-green', amber: 'border-l-warning', blue: 'border-l-sky-300', red: 'border-l-danger' }

/** Métrica de operação: número grande, significado curto e cor sem depender só dela. */
export function MetricCard({ label, value, detail, icon: Icon, tone = 'green' }: MetricCardProps) {
  return <article className={`liquid-glass border-l-2 p-5 transition-colors hover:border-t-brand-green/40 ${TONES[tone]}`}><div className="flex items-center justify-between gap-4"><p className="text-xs uppercase tracking-[0.12em] text-white/45">{label}</p><Icon className="h-4 w-4 text-white/30" aria-hidden="true" /></div><p className="mt-4 font-display text-3xl font-semibold tracking-[-0.04em] text-white">{value}</p>{detail && <p className="mt-2 text-xs text-white/35">{detail}</p>}</article>
}
