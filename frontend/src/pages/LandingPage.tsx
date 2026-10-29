import { ArrowUpRight, CalendarDays, Check, ChevronRight, LogIn, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { LogoMark } from '@/shared/ui/LogoMark'

const programs = [
  { number: '01', name: 'Jiu-Jitsu', detail: 'Disciplina, confiança e presença corporal.' },
  { number: '02', name: 'Música', detail: 'Escuta, expressão e criação em conjunto.' },
  { number: '03', name: 'Balé', detail: 'Movimento, ritmo e descoberta de possibilidades.' },
]

export function LandingPage() {
  usePageTitle('Instituto Livre Acesso')
  const { status } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  if (status === 'signed-in') return <Navigate to="/painel" replace />

  return (
    <div className="landing-page min-h-screen bg-[#f3f6ef] text-[#102012]">
      <header className="landing-header border-b border-[#b8c9b2]">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-5 lg:px-12">
          <Link to="/" className="flex items-center gap-3" aria-label="Instituto Livre Acesso — início">
            <LogoMark className="h-10 w-10" />
            <span className="font-mono text-sm font-bold uppercase tracking-[0.18em]">Livre Acesso</span>
          </Link>
          <nav className={`${menuOpen ? 'flex' : 'hidden'} absolute left-0 right-0 top-[81px] z-20 flex-col border-b border-[#b8c9b2] bg-[#f3f6ef] px-6 py-5 lg:static lg:flex lg:flex-row lg:items-center lg:gap-8 lg:border-0 lg:bg-transparent lg:p-0`}>
            <a href="#instituto" onClick={() => setMenuOpen(false)} className="py-2 font-mono text-xs uppercase tracking-[0.14em] text-[#4b5e4a] hover:text-[#31811f]">O instituto</a>
            <a href="#modalidades" onClick={() => setMenuOpen(false)} className="py-2 font-mono text-xs uppercase tracking-[0.14em] text-[#4b5e4a] hover:text-[#31811f]">Modalidades</a>
            <a href="#acompanhamento" onClick={() => setMenuOpen(false)} className="py-2 font-mono text-xs uppercase tracking-[0.14em] text-[#4b5e4a] hover:text-[#31811f]">Acompanhamento</a>
            <Link to="/entrar" className="mt-3 inline-flex items-center justify-center gap-2 border border-[#31811f] px-4 py-3 font-mono text-xs font-bold uppercase tracking-[0.14em] text-[#246517] lg:mt-0">Entrar <LogIn size={14} /></Link>
          </nav>
          <button type="button" className="border border-[#b8c9b2] p-2 lg:hidden" onClick={() => setMenuOpen((open) => !open)} aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      <main>
        <section className="landing-grid border-b border-[#b8c9b2]">
          <div className="mx-auto grid max-w-[1440px] lg:grid-cols-[1.25fr_.75fr]">
            <div className="border-b border-[#b8c9b2] px-6 py-20 sm:py-28 lg:border-b-0 lg:border-r lg:px-12 lg:py-36">
              <p className="mb-8 font-mono text-xs font-bold uppercase tracking-[0.24em] text-[#31811f]">Instituto Livre Acesso</p>
              <h1 className="max-w-4xl text-[clamp(3.2rem,8vw,8.5rem)] font-black leading-[.88] tracking-[-.08em]">Cuidado que abre caminhos.</h1>
              <div className="mt-10 flex max-w-2xl flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
                <p className="max-w-md font-mono text-base leading-7 text-[#4b5e4a]">Um espaço para crianças e adolescentes desenvolverem corpo, expressão, vínculo e autonomia através da arte e do esporte.</p>
                <a href="#modalidades" className="inline-flex shrink-0 items-center gap-2 font-mono text-xs font-bold uppercase tracking-[0.12em] text-[#246517]">Conheça as modalidades <ArrowUpRight size={16} /></a>
              </div>
            </div>
            <div className="flex min-h-[360px] flex-col justify-between bg-[#dfe9d9] px-6 py-8 lg:min-h-0 lg:px-10 lg:py-12">
              <div className="flex items-start justify-between font-mono text-xs text-[#587052]"><span>01 / 03</span><span>São Paulo, SP</span></div>
              <div>
                <div className="mb-6 h-px w-full bg-[#9db593]" />
                <p className="max-w-sm text-2xl font-bold leading-tight tracking-[-.03em] text-[#21461b]">Acompanhar cada pessoa de perto muda o jeito de cuidar.</p>
                <Link to="/entrar" className="mt-8 inline-flex items-center gap-3 border border-[#31811f] bg-[#31811f] px-5 py-4 font-mono text-xs font-bold uppercase tracking-[0.12em] text-white hover:bg-[#246517]">Acessar o sistema <ChevronRight size={16} /></Link>
              </div>
            </div>
          </div>
        </section>

        <section id="instituto" className="mx-auto grid max-w-[1440px] scroll-mt-8 border-b border-[#b8c9b2] lg:grid-cols-[.75fr_1.25fr]">
          <div className="border-b border-[#b8c9b2] px-6 py-12 lg:border-b-0 lg:border-r lg:px-12"><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-[#31811f]">O instituto</p><p className="mt-6 max-w-xs font-mono text-sm leading-6 text-[#4b5e4a]">Gestão com cuidado, dados e presença. A tecnologia organiza o trabalho para que a equipe possa estar mais perto dos alunos.</p></div>
          <div className="grid sm:grid-cols-3"><div className="border-b border-[#b8c9b2] px-6 py-12 sm:border-b-0 sm:border-r lg:px-10"><span className="font-mono text-4xl font-bold text-[#31811f]">01</span><p className="mt-8 font-mono text-sm leading-6">Cada trajetória é acompanhada de forma individual.</p></div><div className="border-b border-[#b8c9b2] px-6 py-12 sm:border-b-0 sm:border-r lg:px-10"><span className="font-mono text-4xl font-bold text-[#31811f]">02</span><p className="mt-8 font-mono text-sm leading-6">Família, equipe e aluno compartilham o mesmo cuidado.</p></div><div className="px-6 py-12 lg:px-10"><span className="font-mono text-4xl font-bold text-[#31811f]">03</span><p className="mt-8 font-mono text-sm leading-6">Evolução é observada além de uma simples presença.</p></div></div>
        </section>

        <section id="modalidades" className="mx-auto max-w-[1440px] scroll-mt-8 border-b border-[#b8c9b2] px-6 py-16 lg:px-12 lg:py-24"><div className="mb-12 flex flex-col justify-between gap-6 sm:flex-row sm:items-end"><div><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-[#31811f]">Modalidades</p><h2 className="mt-4 max-w-xl text-4xl font-black tracking-[-.05em] sm:text-6xl">Movimento para descobrir possibilidades.</h2></div><p className="max-w-xs font-mono text-sm leading-6 text-[#4b5e4a]">Três caminhos diferentes. O mesmo compromisso com desenvolvimento, convivência e pertencimento.</p></div><div className="grid border-l border-t border-[#b8c9b2] md:grid-cols-3">{programs.map((program) => <article key={program.number} className="border-b border-r border-[#b8c9b2] p-6 transition-colors hover:bg-[#dfe9d9] lg:p-8"><span className="font-mono text-xs text-[#31811f]">{program.number}</span><h3 className="mt-20 text-2xl font-bold tracking-[-.03em]">{program.name}</h3><p className="mt-4 max-w-xs font-mono text-sm leading-6 text-[#4b5e4a]">{program.detail}</p><span className="mt-12 block border-t border-[#b8c9b2] pt-4 font-mono text-xs uppercase tracking-[0.14em] text-[#31811f]">Ver no sistema <ArrowUpRight className="ml-1 inline" size={14} /></span></article>)}</div></section>

        <section id="acompanhamento" className="border-b border-[#b8c9b2] bg-[#102012] text-[#edf4e9] scroll-mt-8"><div className="mx-auto grid max-w-[1440px] lg:grid-cols-[1fr_1fr]"><div className="border-b border-[#4e684c] px-6 py-16 lg:border-b-0 lg:border-r lg:px-12 lg:py-24"><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-[#8dd36f]">Acompanhamento</p><h2 className="mt-5 max-w-xl text-4xl font-black tracking-[-.05em] sm:text-6xl">O desenvolvimento tem muitas formas.</h2><p className="mt-8 max-w-md font-mono text-sm leading-7 text-[#b8c9b2]">A equipe registra evolução, desempenho, interação e participação para construir uma visão mais completa de cada aluno — inclusive para crianças autistas.</p></div><div className="grid sm:grid-cols-2"><div className="border-b border-[#4e684c] px-6 py-10 sm:border-r lg:px-10"><Check className="text-[#8dd36f]" size={20} /><p className="mt-6 font-mono text-sm leading-6">Avaliações periódicas com contexto.</p></div><div className="border-b border-[#4e684c] px-6 py-10 lg:px-10"><CalendarDays className="text-[#8dd36f]" size={20} /><p className="mt-6 font-mono text-sm leading-6">Presença e rotina reunidas no mesmo lugar.</p></div><div className="px-6 py-10 sm:border-r lg:px-10"><Check className="text-[#8dd36f]" size={20} /><p className="mt-6 font-mono text-sm leading-6">Relatório individual para orientar decisões.</p></div><div className="px-6 py-10 lg:px-10"><Check className="text-[#8dd36f]" size={20} /><p className="mt-6 font-mono text-sm leading-6">Histórico para enxergar continuidade.</p></div></div></div></section>

        <section className="mx-auto flex max-w-[1440px] flex-col items-start justify-between gap-8 px-6 py-16 sm:flex-row sm:items-end lg:px-12 lg:py-24"><div><p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-[#31811f]">Para a equipe</p><h2 className="mt-4 max-w-2xl text-4xl font-black tracking-[-.05em] sm:text-6xl">Mais tempo para o que importa.</h2></div><Link to="/entrar" className="inline-flex items-center gap-2 border border-[#31811f] px-5 py-4 font-mono text-xs font-bold uppercase tracking-[0.12em] text-[#246517]">Entrar no sistema <LogIn size={16} /></Link></section>
      </main>
      <footer className="border-t border-[#b8c9b2] px-6 py-6 lg:px-12"><div className="mx-auto flex max-w-[1440px] flex-col justify-between gap-3 font-mono text-xs text-[#587052] sm:flex-row"><span>Instituto Livre Acesso</span><span>Gestão com cuidado, dados e presença.</span></div></footer>
    </div>
  )
}
