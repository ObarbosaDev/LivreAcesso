import { ArrowUp, LogIn, Menu, X } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { useAuth } from '@/app/providers/AuthProvider'
import { usePageTitle } from '@/shared/lib/usePageTitle'

import { aboutParagraph, coreValues, programs } from './content'
import { ProgramPanel } from './ProgramPanel'
import { RevealText } from './RevealText'

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const } },
}

/** Título gigante compartilhado pelas seções: Kanit sólido, sem gradiente — o ponto final é a assinatura. */
function SectionTitle({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <h2
      className={`font-kanit text-[clamp(2rem,6.5vw,6rem)] font-black uppercase leading-[.96] tracking-tight text-white ${className}`}
      style={{ overflowWrap: 'normal', wordBreak: 'normal' }}
    >
      {children}
    </h2>
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

      <header className="relative z-20 border-b border-white/10">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-6 py-5 lg:px-12">
          <a href="#topo" className="flex items-center" aria-label="Voltar ao início da página">
            <img src="/brand/logo-livre-acesso-full.png" alt="Instituto Livre Acesso" className="h-14 w-auto object-contain sm:h-16" />
          </a>
          <nav
            className={`${menuOpen ? 'flex' : 'hidden'} absolute left-0 right-0 top-[81px] z-20 flex-col border-b border-white/10 bg-ink px-6 py-5 lg:static lg:flex lg:flex-row lg:items-center lg:gap-8 lg:border-0 lg:bg-transparent lg:p-0`}
          >
            <a href="#instituto" onClick={() => setMenuOpen(false)} className="py-2 font-mono text-xs uppercase tracking-[0.14em] text-white/55 hover:text-brand-green">O instituto</a>
            <a href="#modalidades" onClick={() => setMenuOpen(false)} className="py-2 font-mono text-xs uppercase tracking-[0.14em] text-white/55 hover:text-brand-green">Projetos</a>
            <Link to="/entrar" className="mt-3 inline-flex items-center justify-center gap-2.5 border border-brand-green px-5 py-3 font-mono text-xs font-bold uppercase tracking-[0.14em] text-brand-green transition hover:bg-brand-green/10 lg:mt-0">Entrar <LogIn size={14} /></Link>
          </nav>
          <button type="button" className="border border-white/20 p-2 text-white lg:hidden" onClick={() => setMenuOpen((open) => !open)} aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}>
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      <main id="conteudo-principal">
        {/* Hero: texto e foto lado a lado, como uma abertura de revista — a foto sangra até a borda. */}
        <section className="border-b border-white/10 lg:grid lg:grid-cols-2 lg:items-stretch">
          <div className="flex flex-col justify-center px-6 py-20 sm:py-28 lg:px-14 lg:py-16">
            <motion.p {...fade} variants={fadeUp} className="mb-6 font-mono text-xs font-bold uppercase tracking-[0.24em] text-brand-green">
              Instituto Livre Acesso · Ceilândia, DF
            </motion.p>
            <motion.h1
              {...fade}
              variants={fadeUp}
              className="font-kanit text-[clamp(2.4rem,6.2vw,5.5rem)] font-black uppercase leading-[.94] tracking-tight text-white"
              style={{ overflowWrap: 'normal', wordBreak: 'normal' }}
            >
              Cuidado que abre caminhos<span className="text-brand-green">.</span>
            </motion.h1>
            <motion.p {...fade} variants={fadeUp} className="mt-8 max-w-md font-mono text-base leading-7 text-white/55">
              ONG desde 2010 que usa a dança, a música e o esporte para abrir caminhos de cultura, educação e
              cidadania para crianças e adolescentes de Ceilândia.
            </motion.p>
          </div>
          <motion.div
            {...fade}
            variants={fadeUp}
            className="relative min-h-[320px] border-t border-white/10 lg:min-h-0 lg:border-l lg:border-t-0"
          >
            <img
              src={programs[0].image.src}
              alt={programs[0].image.alt}
              className="absolute inset-0 h-full w-full object-cover"
            />
          </motion.div>
        </section>

        {/* Faixa fixa de valores — uma frase, sem rolagem infinita. */}
        <div className="border-b border-white/10 px-6 py-5 lg:px-12">
          <p className="mx-auto max-w-[1440px] font-mono text-xs uppercase tracking-[0.2em] text-white/35 sm:text-sm">
            {coreValues.join(' · ')} — desde 2010, em Ceilândia.
          </p>
        </div>

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

        {/* Projetos: dois painéis fotográficos em tela cheia, um por projeto — sem repetir a lista. */}
        <section id="modalidades" className="scroll-mt-8 px-6 pb-10 pt-16 lg:px-12 lg:pb-12 lg:pt-20">
          <motion.div {...fade} variants={fadeUp} className="mx-auto max-w-[1440px]">
            <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-brand-green">Nossos projetos</p>
            <SectionTitle className="mt-4">Dois caminhos, o mesmo cuidado.</SectionTitle>
          </motion.div>
        </section>

        {programs.map((program) => (
          <ProgramPanel key={program.name} program={program} />
        ))}

        {/* Fechamento: retoma o tom do hero antes do rodapé, pra página não cortar seco */}
        <motion.section
          {...fade}
          variants={fadeUp}
          className="border-t border-white/10 px-6 py-20 text-center lg:px-12 lg:py-28"
        >
          <p className="font-kanit text-[clamp(1.6rem,4.5vw,3rem)] font-black uppercase leading-tight tracking-tight text-white/90">
            Cultura, educação e esporte<span className="text-brand-green">.</span>
            <br />
            Desde 2010, em Ceilândia<span className="text-brand-green">.</span>
          </p>
        </motion.section>
      </main>

      <footer className="border-t border-white/10 px-6 py-6 lg:px-12">
        <div className="mx-auto flex max-w-[1440px] flex-col justify-between gap-3 font-mono text-xs text-white/40 sm:flex-row">
          <span>Instituto Livre Acesso</span>
          <span>Ceilândia, Distrito Federal · Desde 2010.</span>
        </div>
      </footer>

      <AnimatePresence>
        {showBackToTop && (
          <motion.a
            href="#topo"
            aria-label="Voltar ao topo"
            initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
            animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-20 right-6 z-30 inline-flex h-12 w-12 items-center justify-center border border-white/20 bg-ink/80 text-white/70 backdrop-blur transition hover:border-brand-green hover:text-brand-green"
          >
            <ArrowUp size={20} />
          </motion.a>
        )}
      </AnimatePresence>
    </div>
  )
}
