/** Espelha StudentOutput do backend (backend/app/modules/students/application/dtos.py). */
export type StudentStatus = 'ativo' | 'inativo'

export interface Student {
  id: string
  full_name: string
  cpf_masked: string
  birth_date: string
  age: number
  status: StudentStatus
  guardian_name: string | null
  guardian_phone_masked: string | null
  created_at: string
  updated_at: string
}

export interface StudentPage {
  items: Student[]
  page: number
  page_size: number
  total: number
  total_pages: number
  has_previous: boolean
  has_next: boolean
}

export const STUDENT_STATUS_LABELS: Record<StudentStatus, string> = {
  ativo: 'Ativo',
  inativo: 'Inativo',
}
