import { cn } from '@/shared/lib/cn'

interface LogoMarkProps {
  className?: string
  /** Mostra só o símbolo (anel), sem o lockup de texto — para espaços muito pequenos. */
  markOnly?: boolean
}

/** Ícone oficial do Instituto, recebido da organização — não mais uma aproximação em SVG. */
export function LogoMark({ className, markOnly = false }: LogoMarkProps) {
  if (markOnly) {
    return (
      <img
        src="/brand/icon-livre-acesso.png"
        alt=""
        aria-hidden="true"
        className={cn('h-8 w-8 object-contain', className)}
      />
    )
  }

  return (
    <div className={cn('flex items-center gap-3', className)} role="img" aria-label="Instituto Livre Acesso">
      <img src="/brand/icon-livre-acesso.png" alt="" aria-hidden="true" className="h-10 w-10 shrink-0 object-contain" />
      <span className="logo-wordmark font-display leading-tight" aria-hidden="true">
        <span className="logo-wordmark-muted block text-[0.6rem] font-semibold tracking-[0.14em]">
          INSTITUTO
        </span>
        <span className="block text-base font-bold tracking-tight">LIVRE ACESSO</span>
      </span>
    </div>
  )
}
