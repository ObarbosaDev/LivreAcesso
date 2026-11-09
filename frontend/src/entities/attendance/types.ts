/** Espelha AttendanceSessionOutput e derivados (backend/app/modules/attendance/application/dtos.py). */
export type AttendanceMarkStatus = 'presente' | 'ausente' | 'justificada'

export const ATTENDANCE_MARK_LABELS: Record<AttendanceMarkStatus, string> = {
  presente: 'Presente',
  ausente: 'Faltou',
  justificada: 'Falta justificada',
}

export interface AttendanceMark {
  enrollment_id: string
  status: AttendanceMarkStatus
  note: string | null
}

export type AttendanceSessionStatus = 'aberta' | 'fechada'

export interface AttendanceSession {
  id: string
  class_id: string
  session_date: string
  status: AttendanceSessionStatus
  marks: AttendanceMark[]
  closed_at: string | null
}

export interface AttendanceSessionSummary {
  id: string
  class_id: string
  session_date: string
  status: AttendanceSessionStatus
  closed_at: string | null
}

export interface AttendanceSessionPage {
  items: AttendanceSessionSummary[]
  total: number
}

export interface AttendanceMonthlySummary {
  enrollment_id: string
  period: string
  total_sessions: number
  present_count: number
  absent_count: number
  justified_count: number
}

export interface AttendanceSummaryPage {
  items: AttendanceMonthlySummary[]
}
