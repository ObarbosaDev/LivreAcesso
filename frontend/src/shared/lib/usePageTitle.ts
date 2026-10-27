import { useEffect } from 'react'

/** Mantém a aba do navegador identificável quando a pessoa abre várias telas do sistema ao mesmo tempo. */
export function usePageTitle(title: string): void {
  useEffect(() => {
    const previous = document.title
    document.title = `${title} · Livre Acesso`
    return () => {
      document.title = previous
    }
  }, [title])
}
