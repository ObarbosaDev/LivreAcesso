import { ArrowUp, LogIn, Menu, X } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { usePageTitle } from '@/shared/lib/usePageTitle'

import { aboutParagraph, marqueeWords, programs } from './content'
import { ProgramStack } from './ProgramStack'
import { RevealText } from './RevealText'

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const } },
}

/** Título gigante compartilhado pelas seções: Kanit, gradiente da marca, sem monoespaçada aqui. */
function SectionTitle({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <h2
      className={`landing-gradient-text font-kanit text-[clamp(2rem,6.5vw,6rem)] font-black uppercase leading-[.96] tracking-tight ${className}`}
      style={{ overflowWrap: 'normal', wordBreak: 'normal' }}
    >
      {children}
    </h2>
  )
}

function Marquee() {
  const row = [...marqueeWords, ...marqueeWords]
  return (
    <div className="overflow-hidden border-y border-white/10 bg-surface-raised py-6 [mask-image:linear-gradient(to_right,transparent,black_6%,black_94%,transparent)]">
      <div className="marquee-track flex w-max gap-10">
        {row.map((word, index) => (
          <span
            key={`${word}-${index}`}
            className="font-kanit text-2xl font-extrabold uppercase tracking-tight text-white/25 sm:text-4xl"
          >
            {word}
          </span>
        ))}
      </div>
    </div>
  )
}

export function LandingPage() {
  usePageTitle('Instituto Livre Acesso')
  const { status } = useAuth()
  const reduceMotion = useReducedMotion()
  const [menuOpen, setMenuOpen] = useState(false)
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    const onScroll = () => setShowBackToTop(window.scrollY > 520)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  if (status === 'signed-in') return <Navigate to="/painel" replace />

  const fade = reduceMotion ? {} : { initial: 'hidden', whileInView: 'shown', viewport: { once: true, margin: '-10%' } }

  return (
    <div id="topo" className="landing-page min-h-screen bg-ink text-white">
      <a
        href="#conteudo-principal"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:bg-brand-green focus:px-4 focus:py-3 focus:font-mono focus:text-xs focus:font-bold focus:text-ink"
      >
        Pular para o conteúdo
      </a>

      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-5 lg:px-12">
          <a href="#topo" className="flex items-center" aria-label="Voltar ao início da página">
            <img src="/brand/logo-livre-acesso-full.png" alt="Instituto Livre Acesso" className="h-14 w-auto object-contain sm:h-16" />
          </a>
          <nav
            className={`${menuOpen ? 'flex' : 'hidden'} absolute left-0 right-0 top-[81px] z-20 flex-col border-b border-white/10 bg-ink px-6 py-5 lg:static lg:flex lg:flex-row lg:items-center lg:gap-8 lg:border-0 lg:bg-transparent lg:p-0`}
          >
            <a href="#instituto" onClick={() => setMenuOpen(false)} className="py-2 font-mono text-xs uppercase tracking-[0.14em] text-white/55 hover:text-brand-green">O instituto</a>
            <a href="#modalidades" onClick={() => setMenuOpen(false)} className="py-2 font-mono text-xs uppercase tracking-[0.14em] text-white/55 hover:text-brand-green">Projetos</a>
            <Link to="/entrar" className="mt-3 inline-flex items-center justify-center gap-2 border border-brand-green px-4 py-3 font-mono text-xs font-bold uppercase tracking-[0.14em] text-brand-green lg:mt-0">Entrar <LogIn size={14} /></Link>
          </nav>
          <button type="button" className="border border-white/20 p-2 text-white lg:hidden" onClick={() => setMenuOpen((open) => !open)} aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      <main id="conteudo-principal">
        {/* Hero */}
        <section className="border-b border-white/10 px-6 py-20 sm:py-28 lg:px-12 lg:py-32">
          <div className="mx-auto max-w-[1440px]">
            <motion.p {...fade} variants={fadeUp} className="mb-6 font-mono text-xs font-bold uppercase tracking-[0.24em] text-brand-green">
              Instituto Livre Acesso · Ceilândia, DF
            </motion.p>
            <motion.h1
              {...fade}
              variants={fadeUp}
              className="landing-gradient-text font-kanit text-[clamp(2.4rem,9vw,8rem)] font-black uppercase leading-[.92] tracking-tight"
              style={{ overflowWrap: 'normal', wordBreak: 'normal' }}
            >
              Cuidado que abre caminhos.
            </motion.h1>
            <motion.p {...fade} variants={fadeUp} className="mt-10 max-w-md font-mono text-base leading-7 text-white/55">
              ONG desde 2010 que usa a dança, a música e o esporte para abrir caminhos de cultura, educação e
              cidadania para crianças e adolescentes de Ceilândia.
            </motion.p>
            <motion.div {...fade} variants={fadeUp} className="mt-14 overflow-hidden border border-white/10">
              <img
                src={programs[0].image.src}
                alt={programs[0].image.alt}
                className="h-[260px] w-full object-cover sm:h-[380px] lg:h-[460px]"
              />
            </motion.div>
          </div>
        </section>

        <Marquee />

        {/* Sobre o instituto */}
        <section id="instituto" className="scroll-mt-8 border-b border-white/10 px-6 py-20 lg:px-12 lg:py-28">
          <div className="mx-auto flex max-w-[1440px] flex-col items-center gap-12 text-center">
            <motion.div {...fade} variants={fadeUp}>
              <p className="mb-5 font-mono text-xs font-bold uppercase tracking-[0.2em] text-brand-green">O instituto</p>
              <SectionTitle>Sobre o Instituto</SectionTitle>
            </motion.div>
            <RevealText text={aboutParagraph} className="max-w-2xl font-mono text-sm leading-7 text-white/60 sm:text-base" />
          </div>
        </section>

        {/* Lista numerada dos dois projetos */}
        <section id="modalidades" className="scroll-mt-8 border-b border-white/10 px-6 py-16 lg:px-12 lg:py-24">
          <div className="mx-auto max-w-[1440px]">
            <motion.div {...fade} variants={fadeUp} className="mb-14">
              <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-brand-green">Nossos projetos</p>
              <SectionTitle className="mt-4">Dois caminhos, o mesmo cuidado.</SectionTitle>
            </motion.div>
            <div className="divide-y divide-white/10 border-t border-white/10">
              {programs.map((program, index) => (
                <motion.div
                  key={program.name}
                  {...fade}
                  variants={fadeUp}
                  transition={{ delay: index * 0.08 }}
                  className="flex flex-col gap-4 py-10 sm:flex-row sm:items-baseline sm:gap-10"
                >
                  <span className="font-kanit text-5xl font-black text-white/15 sm:text-7xl">{program.number}</span>
                  <div>
                    <h3 className="font-kanit text-2xl font-bold uppercase tracking-tight text-white sm:text-4xl">{program.name}</h3>
                    <p className="mt-3 max-w-2xl font-mono text-sm leading-6 text-white/50 sm:text-base">{program.summary}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Cards empilhados com a foto e o texto completo de cada projeto */}
        <section className="px-6 py-16 lg:px-12 lg:py-24">
          <div className="mx-auto max-w-[1440px]">
            <ProgramStack programs={programs} />
          </div>
        </section>
      </main>

      <footer className="border-t border-white/10 px-6 py-6 lg:px-12">
        <div className="mx-auto flex max-w-[1440px] flex-col justify-between gap-3 font-mono text-xs text-white/40 sm:flex-row">
          <span>Instituto Livre Acesso</span>
          <span>Ceilândia, Distrito Federal · Desde 2010.</span>
        </div>
      </footer>

      {showBackToTop && (
        <a
          href="#topo"
          aria-label="Voltar ao topo"
          className="fixed bottom-6 right-6 z-30 inline-flex h-12 w-12 items-center justify-center border border-brand-green bg-ink text-brand-green shadow-[4px_4px_0_var(--color-brand-green)] transition hover:-translate-y-1 hover:bg-brand-green hover:text-ink"
        >
          <ArrowUp size={20} />
        </a>
      )}
    </div>
  )
}
