/** Espelha EnrollmentOutput (backend/app/modules/enrollments/application/dtos.py). */
export type EnrollmentStatus = 'ativa' | 'cancelada'

export interface Enrollment {
  id: string
  student_id: string
  class_id: string
  status: EnrollmentStatus
  created_at: string
  updated_at: string
}

export const ENROLLMENT_STATUS_LABELS: Record<EnrollmentStatus, string> = {
  ativa: 'Ativa',
  cancelada: 'Cancelada',
}
