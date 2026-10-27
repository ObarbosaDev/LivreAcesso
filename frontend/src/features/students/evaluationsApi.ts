import { httpClient } from '@/shared/api/httpClient'
import type { StudentEvaluation } from '@/entities/studentEvaluation/types'
export interface StudentEvaluationPayload { period_start: string; period_end: string; performance_score: number; evolution_score: number; interaction_score: number; participation_score: number; autonomy_score: number; wellbeing_score: number; support_level: string; observations: string; effective_strategies: string; next_objective: string }
export function listStudentEvaluations(studentId: string, signal?: AbortSignal) { return httpClient.get<{ items: StudentEvaluation[] }>(`/api/v1/students/${studentId}/evaluations`, signal) }
export function createStudentEvaluation(studentId: string, payload: StudentEvaluationPayload) { return httpClient.post<StudentEvaluation>(`/api/v1/students/${studentId}/evaluations`, payload) }
