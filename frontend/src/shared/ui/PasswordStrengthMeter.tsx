import { cn } from '@/shared/lib/cn'

interface PasswordStrengthMeterProps {
  password: string
}

function scoreOf(password: string): number {
  if (!password) return 0
  let score = 0
  if (password.length >= 8) score += 1
  if (password.length >= 12) score += 1
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password)) score += 1
  return Math.min(score, 4)
}

const LABELS = ['Muito fraca', 'Fraca', 'Razoável', 'Boa', 'Forte']
const COLORS = ['bg-danger', 'bg-danger', 'bg-warning', 'bg-brand-green-soft', 'bg-brand-green']

/** Força visível além de "mínimo 8 caracteres": ajuda a pessoa a escolher uma senha melhor sem bloquear a decisão dela. */
export function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  const score = scoreOf(password)
  if (!password) return null

  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex gap-1.5">
        {[0, 1, 2, 3].map((segment) => (
          <span
            key={segment}
            className={cn(
              'h-1 flex-1 rounded-full bg-white/10 transition-colors',
              segment < score && COLORS[score],
            )}
          />
        ))}
      </div>
      <p className="mt-1.5 text-xs text-white/40">{LABELS[score]}</p>
    </div>
  )
}
