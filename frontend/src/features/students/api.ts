import { httpClient } from '@/shared/api/httpClient'
import type { Student, StudentPage, StudentStatus } from '@/entities/student/types'

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
