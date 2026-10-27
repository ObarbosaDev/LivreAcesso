import { httpClient } from '@/shared/api/httpClient'
import type { StudentPage, StudentStatus } from '@/entities/student/types'

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
