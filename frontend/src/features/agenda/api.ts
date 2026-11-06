import { httpClient } from '@/shared/api/httpClient'
import type { AgendaEvent, AgendaEventType } from '@/entities/agenda/types'
export interface AgendaEventPayload { title: string; description?: string; event_type: AgendaEventType; starts_at: string; ends_at: string; all_day: boolean; location?: string; class_id?: string; assigned_to?: string }
export async function listAgenda(start: string, end: string, signal?: AbortSignal) {
  const page = await httpClient.get<{ items: AgendaEvent[] }>(
    `/api/v1/agenda?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
    signal,
  )
  return page.items
}
export function createAgendaEvent(payload: AgendaEventPayload) { return httpClient.post<AgendaEvent>('/api/v1/agenda', payload) }
export function updateAgendaEvent(eventId: string, expectedUpdatedAt: string, payload: AgendaEventPayload) { return httpClient.put<AgendaEvent>(`/api/v1/agenda/${eventId}?expected_updated_at=${encodeURIComponent(expectedUpdatedAt)}`, payload) }
export function cancelAgendaEvent(eventId: string, expectedUpdatedAt: string, reason: string) { return httpClient.post<AgendaEvent>(`/api/v1/agenda/${eventId}/cancel?expected_updated_at=${encodeURIComponent(expectedUpdatedAt)}&reason=${encodeURIComponent(reason)}`, {}) }
