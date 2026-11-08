import { motion, useReducedMotion, useScroll, useTransform } from 'motion/react'
import { useRef } from 'react'

import type { Program } from './content'

interface ProgramCardProps {
  program: Program
  index: number
  total: number
}

/** Cada card gruda no topo e encolhe um pouco conforme o próximo card sobe por cima. */
function ProgramCard({ program, index, total }: ProgramCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const reduceMotion = useReducedMotion()
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] })
  const isCovered = total - 1 - index > 0
  const targetScale = 1 - (total - 1 - index) * 0.04
  const targetOpacity = isCovered ? 0.85 : 1
  const scale = useTransform(scrollYProgress, [0, 1], [1, reduceMotion ? 1 : targetScale])
  const opacity = useTransform(scrollYProgress, [0, 1], [1, reduceMotion ? 1 : targetOpacity])

  return (
    <div ref={ref} className="sticky top-20 h-[80vh]" style={{ top: 80 + index * 24 }}>
      <motion.article
        style={{ scale, opacity }}
        className="h-full border border-white/10 bg-surface-raised p-5 shadow-[0_0_60px_-20px_var(--color-brand-green)] sm:p-8 lg:p-10"
      >
        <div className="flex items-baseline gap-4 border-b border-white/10 pb-6">
          <span className="font-kanit text-5xl font-black text-brand-green/40 sm:text-7xl">{program.number}</span>
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-brand-green">{program.since}</p>
            <h3 className="mt-1 font-kanit text-2xl font-extrabold tracking-tight text-white sm:text-4xl">
              {program.name}
            </h3>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_.9fr] lg:items-center">
          <p className="max-w-xl font-mono text-sm leading-7 text-white/65 sm:text-base">{program.description}</p>
          <div className="h-[220px] overflow-hidden sm:h-[280px] lg:h-[320px]">
            <img
              src={program.image.src}
              alt={program.image.alt}
              loading="lazy"
              className="h-full w-full object-cover"
            />
          </div>
        </div>

        {program.methodology && (
          <ul className="mt-6 flex flex-wrap gap-x-6 gap-y-2 border-t border-white/10 pt-5">
            {program.methodology.map((item) => (
              <li key={item} className="font-mono text-xs text-white/45">
                {item}
              </li>
            ))}
          </ul>
        )}
      </motion.article>
    </div>
  )
}

export function ProgramStack({ programs }: { programs: Program[] }) {
  return (
    <div className="flex flex-col gap-10">
      {programs.map((program, index) => (
        <ProgramCard key={program.name} program={program} index={index} total={programs.length} />
      ))}
    </div>
  )
}
