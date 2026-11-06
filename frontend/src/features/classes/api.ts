import { httpClient } from '@/shared/api/httpClient'
import type { ClassPage, ClassSchedule, Modality, ModalityPage, Unit } from '@/entities/class/types'

interface ListClassesParams {
  active?: boolean
  modalityId?: string
  unit?: Unit
  query?: string
  page: number
  pageSize: number
  signal?: AbortSignal
}

export function listClasses({ active, modalityId, unit, query, page, pageSize, signal }: ListClassesParams) {
  const params = new URLSearchParams()
  if (active !== undefined) params.set('active', String(active))
  if (query) params.set('query', query)
  if (modalityId) params.set('modality_id', modalityId)
  if (unit) params.set('unit', unit)
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

export function listModalities(active = true, signal?: AbortSignal) {
  const params = new URLSearchParams({ active: String(active), page: '1', page_size: '100' })
  return httpClient.get<ModalityPage>(`/api/v1/modalities?${params.toString()}`, signal)
}

export function createModality(payload: { name: string; description?: string }) {
  return httpClient.post<Modality>('/api/v1/modalities', payload)
}

export interface CreateClassPayload {
  modality_id: string
  unit: Unit
  name: string
  capacity: number
  location: string
  minimum_age?: number
  maximum_age?: number
  schedules: ClassSchedule[]
  instructor_ids: string[]
}

export function createClass(payload: CreateClassPayload) {
  return httpClient.post('/api/v1/classes', payload)
}
