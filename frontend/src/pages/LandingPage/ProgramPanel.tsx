import { motion, useReducedMotion } from 'motion/react'

import type { Program } from './content'

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const } },
}

/**
 * Painel fotográfico em tela cheia por projeto — não um card de SaaS.
 * O número gigante ao fundo é o único enfeite: tudo o mais é a foto real e o texto.
 */
export function ProgramPanel({ program }: { program: Program }) {
  const reduceMotion = useReducedMotion()
  const fade = reduceMotion ? {} : { initial: 'hidden', whileInView: 'shown', viewport: { once: true, margin: '-15%' } }

  return (
    <section className="relative min-h-[82vh] overflow-hidden border-t border-white/10">
      <span
        aria-hidden="true"
        className="pointer-events-none absolute -left-4 -top-10 select-none font-kanit text-[13rem] font-black leading-none text-white/[0.04] sm:text-[18rem]"
      >
        {program.number}
      </span>
      <img
        src={program.image.src}
        alt={program.image.alt}
        loading="lazy"
        className="absolute inset-0 h-full w-full object-cover"
        style={{ objectPosition: program.image.position ?? 'center' }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-ink from-5% via-ink/92 via-70% to-ink/20 to-100%" aria-hidden="true" />

      <motion.div {...fade} variants={fadeUp} className="relative z-10 flex min-h-[82vh] flex-col justify-end px-6 py-14 lg:px-14 lg:py-16">
        <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-brand-green">{program.since}</p>
        <h3 className="mt-3 max-w-3xl font-kanit text-[clamp(2.2rem,7vw,5.5rem)] font-black uppercase leading-[.94] tracking-tight text-white">
          {program.name}
        </h3>
        <p className="mt-6 max-w-xl font-mono text-sm leading-7 text-white/75 sm:text-base">{program.description}</p>
        {program.methodology && (
          <ul className="mt-7 flex flex-wrap gap-x-8 gap-y-2">
            {program.methodology.map((item) => (
              <li key={item} className="border-l border-brand-green/50 pl-3 font-mono text-xs text-white/55">
                {item}
              </li>
            ))}
          </ul>
        )}
      </motion.div>
    </section>
  )
}
