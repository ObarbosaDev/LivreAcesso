import type { ReactNode } from 'react'

interface PageFrameProps { eyebrow?: string; title: string; description?: string; actions?: ReactNode; children: ReactNode }

/** Estrutura comum das áreas do ERP: contexto, título, ação primária e conteúdo. */
export function PageFrame({ eyebrow, title, description, actions, children }: PageFrameProps) {
  return <div className="page-enter mx-auto max-w-[1400px] pb-12"><header className="border-b border-white/10 pb-6"><div className="flex flex-wrap items-end justify-between gap-5"><div><>{eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-green">{eyebrow}</p>}</><h1 className="mt-2 font-display text-4xl font-semibold tracking-[-0.04em] text-white">{title}</h1>{description && <p className="mt-2 max-w-2xl text-sm leading-6 text-white/50">{description}</p>}</div>{actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}</div></header><div className="mt-8">{children}</div></div>
}
