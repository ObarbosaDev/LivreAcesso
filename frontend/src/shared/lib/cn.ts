import { clsx, type ClassValue } from 'clsx'

/** Combina classes condicionalmente sem puxar uma dependência de merge que o projeto não precisa ainda. */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs)
}
