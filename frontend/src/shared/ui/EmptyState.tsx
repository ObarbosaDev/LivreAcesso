import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps { icon: LucideIcon; title: string; description: string; action?: ReactNode }

/** Estado vazio orientado à próxima ação, sem deixar o usuário diante de uma tela morta. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return <div className="border border-dashed border-white/15 bg-white/[.018] px-6 py-10"><div className="flex items-start gap-4"><span className="flex h-9 w-9 shrink-0 items-center justify-center border border-brand-green/30 text-brand-green"><Icon className="h-4 w-4" aria-hidden="true" /></span><div><h2 className="font-display text-sm font-semibold text-white">{title}</h2><p className="mt-2 max-w-xl text-sm leading-6 text-white/45">{description}</p>{action && <div className="mt-5">{action}</div>}</div></div></div>
}
