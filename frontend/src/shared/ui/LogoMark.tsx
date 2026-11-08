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
    <img
      src="/brand/logo-livre-acesso-full.png"
      alt="Instituto Livre Acesso"
      className={cn('h-11 w-auto object-contain', className)}
    />
  )
}
