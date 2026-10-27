import { httpClient } from '@/shared/api/httpClient'
import type { ClassPage } from '@/entities/class/types'

interface ListClassesParams {
  active?: boolean
  query?: string
  page: number
  pageSize: number
  signal?: AbortSignal
}

export function listClasses({ active, query, page, pageSize, signal }: ListClassesParams) {
  const params = new URLSearchParams()
  if (active !== undefined) params.set('active', String(active))
  if (query) params.set('query', query)
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  return httpClient.get<ClassPage>(`/api/v1/classes?${params.toString()}`, signal)
}

interface OccupancyResult {
  class_id: string
  capacity: number
  enrolled: number
  available: number
}

export function getClassOccupancy(classId: string, signal?: AbortSignal) {
  return httpClient.get<OccupancyResult>(`/api/v1/enrollments/occupancy/${classId}`, signal)
}
