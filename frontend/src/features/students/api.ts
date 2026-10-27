import { httpClient } from '@/shared/api/httpClient'
import type { Student, StudentDetail, StudentPage, StudentStatus } from '@/entities/student/types'
import type {
  GuardianDetail,
  GuardianListResult,
  GuardianRelationship,
} from '@/entities/guardian/types'

export interface RegisterStudentPayload {
  full_name: string
  cpf: string
  birth_date: string
  guardian: {
    full_name: string
    phone: string
    email?: string
  }
}

export function registerStudent(payload: RegisterStudentPayload) {
  return httpClient.post<Student>('/api/v1/students', payload)
}

export function getStudentSummary(studentId: string, signal?: AbortSignal) {
  return httpClient.get<Student>(`/api/v1/students/${studentId}`, signal)
}

export function getStudentDetail(studentId: string, signal?: AbortSignal) {
  return httpClient.get<StudentDetail>(`/api/v1/students/${studentId}`, signal)
}

interface ListStudentsParams {
  status?: StudentStatus
  query?: string
  page: number
  pageSize: number
  signal?: AbortSignal
}

export function listStudents({ status, query, page, pageSize, signal }: ListStudentsParams) {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (query) params.set('query', query)
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  return httpClient.get<StudentPage>(`/api/v1/students?${params.toString()}`, signal)
}

export function updateStudent(
  studentId: string,
  payload: { expected_updated_at: string; full_name: string; birth_date: string },
) {
  return httpClient.put<StudentDetail>(`/api/v1/students/${studentId}`, payload)
}

export function changeStudentStatus(
  studentId: string,
  action: 'activate' | 'deactivate',
  payload: { expected_updated_at: string; reason: string },
) {
  return httpClient.post<StudentDetail>(`/api/v1/students/${studentId}/${action}`, payload)
}

export function listGuardians(studentId: string, signal?: AbortSignal) {
  return httpClient.get<GuardianListResult>(`/api/v1/students/${studentId}/guardians`, signal)
}

export function getGuardian(studentId: string, guardianId: string, signal?: AbortSignal) {
  return httpClient.get<GuardianDetail>(
    `/api/v1/students/${studentId}/guardians/${guardianId}`,
    signal,
  )
}

export interface AddGuardianPayload {
  expected_student_updated_at: string
  relationship: GuardianRelationship
  receives_communications: boolean
  make_primary: boolean
  guardian?: { full_name: string; phone: string; email?: string }
  existing_guardian_id?: string
}

export function addGuardian(studentId: string, payload: AddGuardianPayload) {
  return httpClient.post<GuardianDetail>(`/api/v1/students/${studentId}/guardians`, payload)
}

export interface UpdateGuardianPayload {
  expected_student_updated_at: string
  expected_guardian_updated_at: string
  full_name: string
  phone: string
  email?: string
  relationship: GuardianRelationship
  receives_communications: boolean
}

export function updateGuardian(studentId: string, guardianId: string, payload: UpdateGuardianPayload) {
  return httpClient.put<GuardianDetail>(
    `/api/v1/students/${studentId}/guardians/${guardianId}`,
    payload,
  )
}

export function setPrimaryGuardian(
  studentId: string,
  guardianId: string,
  expectedStudentUpdatedAt: string,
) {
  return httpClient.post<GuardianDetail>(
    `/api/v1/students/${studentId}/guardians/${guardianId}/primary`,
    { expected_student_updated_at: expectedStudentUpdatedAt },
  )
}

export function unlinkGuardian(
  studentId: string,
  guardianId: string,
  payload: { expected_student_updated_at: string; reason: string },
) {
  return httpClient.post<{ student_id: string; guardian_id: string; student_updated_at: string }>(
    `/api/v1/students/${studentId}/guardians/${guardianId}/unlink`,
    payload,
  )
}
