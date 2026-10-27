import { Loader2 } from 'lucide-react'

interface FullScreenStateProps {
  title: string
  description: string
  loading?: boolean
  actionHref?: string
  actionLabel?: string
}

/** Tela cheia para carregamento, erro de configuração e falta de acesso — nunca um fundo em branco sem explicação. */
export function FullScreenState({
  title,
  description,
  loading = false,
  actionHref,
  actionLabel,
}: FullScreenStateProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ink px-6">
      <div className="liquid-glass max-w-sm rounded-2xl p-8 text-center">
        {loading && (
          <Loader2
            className="mx-auto mb-4 h-6 w-6 animate-spin text-brand-green"
            aria-hidden="true"
          />
        )}
        <h1 className="font-display text-lg font-semibold text-white">{title}</h1>
        <p className="mt-2 text-sm text-white/60">{description}</p>
        {actionHref && actionLabel && (
          <a
            href={actionHref}
            className="mt-6 inline-flex h-10 items-center justify-center rounded-lg bg-brand-green px-5 text-sm font-semibold text-ink transition hover:bg-brand-green-soft"
          >
            {actionLabel}
          </a>
        )}
      </div>
    </div>
  )
}
