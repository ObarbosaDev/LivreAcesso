import { Loader2 } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'
import { forwardRef } from 'react'

import { cn } from '@/shared/lib/cn'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'md' | 'sm'
  loading?: boolean
}

/** Mesma gramática visual nas três variantes: borda + preenchimento sutil em repouso,
 * cor sólida só no hover. Evita cantos de tela gritando verde/vermelho ao mesmo tempo. */
const VARIANT_CLASSES: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary: 'border-brand-green/70 bg-brand-green/12 text-brand-green hover:border-brand-green hover:bg-brand-green hover:text-ink',
  secondary: 'border-white/15 bg-white/8 text-white hover:bg-white/12',
  danger: 'border-danger/50 bg-danger/10 text-danger hover:border-danger hover:bg-danger hover:text-ink',
}

const SIZE_CLASSES: Record<NonNullable<ButtonProps['size']>, string> = {
  md: 'min-h-11 gap-2 px-5 text-sm',
  sm: 'min-h-8 gap-1.5 px-3 text-xs',
}

/** Botão acessível: estado de carregamento visível, nunca só desabilitado em silêncio. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading = false, disabled, className, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading}
      className={cn(
        'inline-flex items-center justify-center border font-semibold transition duration-150 hover:-translate-y-px active:translate-y-0 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
        SIZE_CLASSES[size],
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
