import { Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'

type Theme = 'dark' | 'light'

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem('livre-acesso-theme') as Theme) || 'dark')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('livre-acesso-theme', theme)
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#000000' : '#f1f3ed')
  }, [theme])

  return <button type="button" onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')} className="theme-toggle inline-flex items-center gap-2 border border-white/15 px-3 py-2 text-xs text-white/60 transition hover:border-brand-green hover:text-brand-green" aria-label={theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'}>{theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}{theme === 'dark' ? 'Claro' : 'Escuro'}</button>
}
