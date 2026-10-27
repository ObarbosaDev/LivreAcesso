/** Espelha ModalityOutput/ClassOutput (backend/app/modules/classes/application/dtos.py). */
export const WEEKDAYS = [
  'segunda',
  'terca',
  'quarta',
  'quinta',
  'sexta',
  'sabado',
  'domingo',
] as const
export type Weekday = (typeof WEEKDAYS)[number]

export const WEEKDAY_LABELS: Record<Weekday, string> = {
  segunda: 'Segunda',
  terca: 'Terça',
  quarta: 'Quarta',
  quinta: 'Quinta',
  sexta: 'Sexta',
  sabado: 'Sábado',
  domingo: 'Domingo',
}

export interface Modality {
  id: string
  name: string
  description: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export interface ModalityPage {
  items: Modality[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface ClassSchedule {
  weekday: Weekday
  starts_at: string
  ends_at: string
}

export interface ClassInstructor {
  id: string
  full_name: string
}

export interface SchoolClass {
  id: string
  modality_id: string
  name: string
  capacity: number
  location: string
  minimum_age: number | null
  maximum_age: number | null
  schedules: ClassSchedule[]
  instructors: ClassInstructor[]
  active: boolean
  created_at: string
  updated_at: string
}

export interface ClassPage {
  items: SchoolClass[]
  page: number
  page_size: number
  total: number
  total_pages: number
}
