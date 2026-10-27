import { usePageTitle } from '@/shared/lib/usePageTitle'

interface ComingSoonPageProps {
  title: string
}

/** Espaço reservado honesto: a rota existe no menu, mas a tela ainda não foi construída. */
export function ComingSoonPage({ title }: ComingSoonPageProps) {
  usePageTitle(title)
  return (
    <div className="max-w-xl">
      <h1 className="font-display text-2xl font-semibold text-white">{title}</h1>
      <p className="mt-2 text-sm text-white/55">Esta área ainda está sendo construída.</p>
    </div>
  )
}
