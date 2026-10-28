import { Loader2 } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'
import { forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  loading?: boolean
}

const VARIANT_CLASSES: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary: 'bg-brand-green text-ink hover:bg-brand-green-soft',
  secondary: 'bg-white/8 text-white border border-white/15 hover:bg-white/12',
  danger: 'bg-danger/90 text-white hover:bg-danger',
}

/** Botão acessível: estado de carregamento visível, nunca só desabilitado em silêncio. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', loading = false, disabled, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading}
      className={cn(
        'inline-flex min-h-11 items-center justify-center gap-2 border px-5 text-sm font-semibold transition duration-150 hover:-translate-y-px active:translate-y-0 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
        VARIANT_CLASSES[variant],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  )
})
