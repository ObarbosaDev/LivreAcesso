import { httpClient } from '@/shared/api/httpClient'
import type { Enrollment } from '@/entities/enrollment/types'

interface ListEnrollmentsParams {
  classId: string
  status?: 'ativa' | 'cancelada'
  page: number
  pageSize: number
  signal?: AbortSignal
}

export function listEnrollments({ classId, status, page, pageSize, signal }: ListEnrollmentsParams) {
  const params = new URLSearchParams()
  params.set('class_id', classId)
  if (status) params.set('status_filter', status)
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  return httpClient.get<{ items: Enrollment[]; total: number; total_pages: number }>(
    `/api/v1/enrollments?${params.toString()}`,
    signal,
  )
}

export function createEnrollment(studentId: string, classId: string) {
  return httpClient.post<Enrollment>('/api/v1/enrollments', {
    student_id: studentId,
    class_id: classId,
  })
}
