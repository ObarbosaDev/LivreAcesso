import { cn } from '@/shared/lib/cn'

interface StatusBadgeProps {
  label: string
  tone: 'success' | 'neutral' | 'warning' | 'danger'
}

const TONE_CLASSES: Record<StatusBadgeProps['tone'], string> = {
  success: 'bg-brand-green/15 text-brand-green',
  neutral: 'bg-white/10 text-white/60',
  warning: 'bg-warning/15 text-warning',
  danger: 'bg-danger/15 text-danger',
}

/** Nunca depende só da cor: o texto do status sempre acompanha a bolinha. */
export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        TONE_CLASSES[tone],
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {label}
    </span>
  )
}
