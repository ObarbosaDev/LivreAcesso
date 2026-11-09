import { httpClient } from '@/shared/api/httpClient'
import type {
  AttendanceMark,
  AttendanceSession,
  AttendanceSessionPage,
  AttendanceSummaryPage,
} from '@/entities/attendance/types'

export function openAttendanceSession(classId: string, sessionDate: string) {
  return httpClient.post<AttendanceSession>('/api/v1/attendance/sessions', {
    class_id: classId,
    session_date: sessionDate,
  })
}

export interface AttendanceMarkPayload {
  enrollment_id: string
  status: AttendanceMark['status']
  note?: string
}

export function recordAttendanceMarks(sessionId: string, marks: AttendanceMarkPayload[]) {
  return httpClient.put<AttendanceSession>(`/api/v1/attendance/sessions/${sessionId}/marks`, marks)
}

export function closeAttendanceSession(sessionId: string) {
  return httpClient.post<AttendanceSession>(`/api/v1/attendance/sessions/${sessionId}/close`)
}

export function listAttendanceSessions(classId: string, limit = 60, offset = 0, signal?: AbortSignal) {
  const params = new URLSearchParams({
    class_id: classId,
    limit: String(limit),
    offset: String(offset),
  })
  return httpClient.get<AttendanceSessionPage>(`/api/v1/attendance/sessions?${params.toString()}`, signal)
}

export function getAttendanceSessionMarks(sessionId: string, signal?: AbortSignal) {
  return httpClient.get<AttendanceMark[]>(`/api/v1/attendance/sessions/${sessionId}/marks`, signal)
}

export function getAttendanceSummary(classId: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ class_id: classId })
  return httpClient.get<AttendanceSummaryPage>(`/api/v1/attendance/summary?${params.toString()}`, signal)
}
