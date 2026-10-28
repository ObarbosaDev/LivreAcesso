import { httpClient } from '@/shared/api/httpClient'
import type { AgendaEvent, AgendaEventType } from '@/entities/agenda/types'
export interface AgendaEventPayload { title: string; description?: string; event_type: AgendaEventType; starts_at: string; ends_at: string; all_day: boolean; location?: string; class_id?: string; assigned_to?: string }
export function listAgenda(start: string, end: string, signal?: AbortSignal) { return httpClient.get<AgendaEvent[]>(`/api/v1/agenda?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`, signal) }
export function createAgendaEvent(payload: AgendaEventPayload) { return httpClient.post<AgendaEvent>('/api/v1/agenda', payload) }
