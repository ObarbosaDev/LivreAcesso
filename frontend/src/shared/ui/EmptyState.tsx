import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps { icon: LucideIcon; title: string; description: string; action?: ReactNode }

/** Estado vazio orientado à próxima ação, sem deixar o usuário diante de uma tela morta. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return <div className="rounded-3xl border border-dashed border-white/12 bg-white/[.018] px-6 py-16 text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-green/10 text-brand-green"><Icon className="h-6 w-6" aria-hidden="true" /></span><h2 className="mt-5 font-display text-lg font-semibold text-white">{title}</h2><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-white/45">{description}</p>{action && <div className="mt-6">{action}</div>}</div>
}
