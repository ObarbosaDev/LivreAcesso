import { cn } from '@/shared/lib/cn'

interface LogoMarkProps {
  className?: string
  /** Mostra só o símbolo (anel), sem o lockup de texto — para espaços muito pequenos. */
  markOnly?: boolean
}

/**
 * Logo própria em vetor, não a foto original: o arquivo recebido era um JPEG
 * comprimido com fundo branco, ilegível em qualquer tamanho pequeno. Como
 * vetor, o anel e o texto ficam nítidos em qualquer escala e usam a mesma
 * fonte (Archivo) do resto do produto, em vez de depender de uma imagem
 * rasterizada deformada pelo recorte.
 */
export function LogoMark({ className, markOnly = false }: LogoMarkProps) {
  if (markOnly) {
    return (
      <svg viewBox="0 0 64 64" className={cn('h-8 w-8', className)} aria-hidden="true">
        <path
          d="M8 24a24 24 0 0 1 48 0"
          stroke="var(--color-brand-green)"
          strokeWidth="9"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M8 40a24 24 0 0 0 48 0"
          stroke="var(--color-brand-green)"
          strokeWidth="9"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
    )
  }

  return (
    <div className={cn('flex items-center gap-3', className)} role="img" aria-label="Instituto Livre Acesso">
      <svg viewBox="0 0 64 64" className="h-10 w-10 shrink-0" aria-hidden="true">
        <path
          d="M8 24a24 24 0 0 1 48 0"
          stroke="var(--color-brand-green)"
          strokeWidth="9"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M8 40a24 24 0 0 0 48 0"
          stroke="var(--color-brand-green)"
          strokeWidth="9"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
      <span className="logo-wordmark font-display leading-tight" aria-hidden="true">
        <span className="logo-wordmark-muted block text-[0.6rem] font-semibold tracking-[0.14em]">
          INSTITUTO
        </span>
        <span className="block text-base font-bold tracking-tight">LIVRE ACESSO</span>
      </span>
    </div>
  )
}
