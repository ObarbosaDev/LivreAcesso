import { Hammer } from 'lucide-react'

import { usePageTitle } from '@/shared/lib/usePageTitle'

interface ComingSoonPageProps {
  title: string
}

/** Espaço reservado honesto: a rota existe no menu, mas a tela ainda não foi construída. */
export function ComingSoonPage({ title }: ComingSoonPageProps) {
  usePageTitle(title)
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="liquid-glass flex h-14 w-14 items-center justify-center rounded-2xl">
        <Hammer className="h-6 w-6 text-brand-green" aria-hidden="true" />
      </div>
      <h1 className="mt-6 font-display text-2xl font-semibold text-white">{title}</h1>
      <p className="mt-2 max-w-sm text-sm text-white/55">
        Esta área ainda está sendo construída. Ela vai aparecer aqui assim que estiver pronta para
        uso real.
      </p>
    </div>
  )
}
