import { CalendarRange, ClipboardList, ShieldCheck, Users } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { LogoMark } from '@/shared/ui/LogoMark'

const container = {
  hidden: { opacity: 0 },
  shown: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
}

const item = {
  hidden: { opacity: 0, y: 12 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as const } },
}

const drawLine = {
  hidden: { scaleX: 0, opacity: 0 },
  shown: { scaleX: 1, opacity: 1, transition: { duration: 0.6, ease: [0.65, 0, 0.35, 1] as const } },
}

const MODULES = [
  { icon: Users, label: 'Estudantes e responsáveis' },
  { icon: CalendarRange, label: 'Modalidades e turmas' },
  { icon: ClipboardList, label: 'Matrículas e ocupação' },
  { icon: ShieldCheck, label: 'Acesso por papel, auditado' },
]

/**
 * Faixa rolando com os módulos reais do sistema, não depoimentos
 * inventados: o produto ainda não tem usuários para citar, e fingir que tem
 * quebraria a confiança de quem vai registrar dados de crianças aqui.
 */
function ModuleMarquee() {
  const chips = [...MODULES, ...MODULES]
  return (
    <div className="relative mt-10 overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
      <div className="marquee-track flex w-max gap-3">
        {chips.map(({ icon: Icon, label }, index) => (
          <span
            key={`${label}-${index}`}
            className="liquid-glass flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-xs font-medium text-white/75"
          >
            <Icon className="h-3.5 w-3.5 text-brand-green" aria-hidden="true" />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}

/**
 * Três anéis concêntricos no canto inferior direito, vazio no layout: o
 * mesmo desenho do símbolo da marca, em escala arquitetônica. Confinados a
 * uma moldura própria para nunca cruzar o título ou o parágrafo — um
 * elemento decorativo não pode atrapalhar a leitura.
 */
function GatewayRings() {
  return <div aria-hidden="true" className="pointer-events-none absolute bottom-12 right-12 h-40 w-40 border-r border-t border-brand-green/25"><span className="absolute right-3 top-3 font-display text-[10px] text-brand-green/50">LA / 01</span></div>
}

function SignalPanel() {
  return <div className="mt-12 grid grid-cols-2 border border-white/10 bg-black/20 text-xs text-white/55"><div className="border-b border-r border-white/10 p-4"><p className="text-brand-green">01</p><p className="mt-2">Cuidado</p></div><div className="border-b border-white/10 p-4"><p className="text-brand-green">02</p><p className="mt-2">Presença</p></div><div className="border-r border-white/10 p-4"><p className="text-brand-green">03</p><p className="mt-2">Evolução</p></div><div className="p-4"><p className="text-brand-green">04</p><p className="mt-2">Continuidade</p></div></div>
}

interface AuthHeroProps {
  title: ReactNode
  description: string
  showModules?: boolean
}

/** Painel esquerdo compartilhado pelas telas de acesso (entrar, recuperar e redefinir senha). */
export function AuthHero({ title, description, showModules = true }: AuthHeroProps) {
  const reduceMotion = useReducedMotion()
  const motionProps = reduceMotion ? {} : { initial: 'hidden', animate: 'shown' }

  return (
    <section className="auth-hero relative hidden w-[46%] flex-col justify-between overflow-hidden border-r border-white/8 bg-surface lg:flex lg:px-14 lg:py-14">
      <GatewayRings />

      <motion.div {...motionProps} variants={container}>
        <motion.div variants={item}>
          <Link to="/" aria-label="Voltar para o Instituto Livre Acesso" className="inline-flex rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-green">
            <LogoMark className="relative" />
          </Link>
        </motion.div>
      </motion.div>

      <motion.div {...motionProps} variants={container} className="relative max-w-md">
        <motion.h1
          variants={item}
          className="font-display text-[3.25rem] font-semibold leading-[1.02] tracking-tight text-white"
        >
          {title}
        </motion.h1>
        <motion.p variants={item} className="mt-6 max-w-sm text-base leading-relaxed text-white/60">
          {description}
        </motion.p>
        {showModules && (
          <motion.div variants={item}>
            <ModuleMarquee />
            <SignalPanel />
          </motion.div>
        )}
      </motion.div>

      <motion.div {...motionProps} variants={container} className="relative flex items-center gap-4">
        <motion.span variants={drawLine} className="h-px w-10 origin-left bg-white/20" />
        <motion.p variants={item} className="text-sm text-white/35">
          Ceilândia, Distrito Federal
        </motion.p>
      </motion.div>
    </section>
  )
}

/** Cartão de vidro compartilhado pelas telas de acesso, com a logo visível só no celular. */
export function AuthPanel({ children }: { children: ReactNode }) {
  const reduceMotion = useReducedMotion()
  return (
    <section className="flex flex-1 flex-col items-center justify-center px-6 py-12 sm:px-12">
      <motion.div
        initial={reduceMotion ? undefined : { opacity: 0, y: 8 }}
        animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="liquid-glass w-full max-w-sm rounded-2xl p-8 sm:p-10"
      >
        <div className="mb-8 lg:hidden">
          <Link to="/" aria-label="Voltar para o Instituto Livre Acesso" className="inline-flex rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-green">
            <LogoMark />
          </Link>
        </div>
        {children}
      </motion.div>
    </section>
  )
}
