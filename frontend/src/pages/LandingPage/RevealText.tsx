import { motion, useReducedMotion } from 'motion/react'

interface RevealTextProps {
  text: string
  className?: string
}

/**
 * Revela o parágrafo palavra por palavra quando ele entra na tela. Palavra
 * (não caractere) para não inflar o DOM com um nó por letra num texto longo.
 */
export function RevealText({ text, className }: RevealTextProps) {
  const reduceMotion = useReducedMotion()
  const words = text.split(' ')

  if (reduceMotion) {
    return <p className={className}>{text}</p>
  }

  return (
    <p className={className}>
      {words.map((word, index) => (
        <motion.span
          key={`${word}-${index}`}
          initial={{ opacity: 0.2 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: '-10% 0px' }}
          transition={{ duration: 0.4, delay: index * 0.012 }}
          className="inline-block"
        >
          {word}
          {index < words.length - 1 ? ' ' : ''}
        </motion.span>
      ))}
    </p>
  )
}
