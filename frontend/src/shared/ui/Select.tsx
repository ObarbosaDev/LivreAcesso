import { ChevronDown } from 'lucide-react'
import type { SelectHTMLAttributes } from 'react'
import { forwardRef, useId } from 'react'

import { cn } from '@/shared/lib/cn'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  error?: string
  hint?: string
  options: readonly SelectOption[]
}

/** Select com a mesma linguagem visual do Input: rótulo associado, seta própria em vez da do navegador, erro anunciado por aria-describedby. */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, hint, options, id, className, ...props },
  ref,
) {
  const autoId = useId()
  const selectId = id ?? autoId
  const hintId = hint ? `${selectId}-hint` : undefined
  const errorId = error ? `${selectId}-error` : undefined

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={selectId} className="text-sm font-medium text-white">
        {label}
      </label>
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          aria-invalid={Boolean(error)}
          aria-describedby={cn(hintId, errorId) || undefined}
          className={cn(
            'h-12 w-full appearance-none border border-white/10 bg-white/5 pl-4 pr-10 text-white outline-none transition focus:border-brand-green focus:bg-white/8 focus:ring-4 focus:ring-brand-green/15',
            error && 'border-danger/70',
            className,
          )}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value} className="bg-surface">
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40"
          aria-hidden="true"
        />
      </div>
      {hint && !error && (
        <p id={hintId} className="text-xs text-white/40">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  )
})
