import { cn } from '@/shared/lib/cn'

interface OccupancyBarProps {
  capacity: number
  enrolled: number
}

/** Nunca depende só da cor: a barra sempre vem acompanhada dos números exatos. */
export function OccupancyBar({ capacity, enrolled }: OccupancyBarProps) {
  const ratio = capacity > 0 ? Math.min(enrolled / capacity, 1) : 0
  const full = enrolled >= capacity

  return (
    <div className="flex flex-col gap-1.5">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/8">
        <div
          className={cn('h-full rounded-full', full ? 'bg-warning' : 'bg-brand-green')}
          style={{ width: `${ratio * 100}%` }}
        />
      </div>
      <p className="text-xs text-white/50">
        {enrolled}/{capacity} vagas ocupadas{full && ' · turma cheia'}
      </p>
    </div>
  )
}
