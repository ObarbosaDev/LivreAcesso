import { motion, useReducedMotion } from 'motion/react'

/** Confirmação visual de uma ação concluída: o traço se desenha uma vez, sem repetir, sem exagero. */
export function SuccessCheck() {
  const reduceMotion = useReducedMotion()

  return (
    <svg viewBox="0 0 64 64" className="h-16 w-16" aria-hidden="true">
      <motion.circle
        cx="32"
        cy="32"
        r="28"
        fill="none"
        stroke="var(--color-brand-green)"
        strokeWidth="3"
        initial={reduceMotion ? undefined : { pathLength: 0, opacity: 0 }}
        animate={reduceMotion ? undefined : { pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.65, 0, 0.35, 1] }}
      />
      <motion.path
        d="M20 33l8 8 16-17"
        fill="none"
        stroke="var(--color-brand-green)"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={reduceMotion ? undefined : { pathLength: 0 }}
        animate={reduceMotion ? undefined : { pathLength: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut', delay: reduceMotion ? 0 : 0.5 }}
      />
    </svg>
  )
}
