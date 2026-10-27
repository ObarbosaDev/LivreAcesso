import { httpClient } from '@/shared/api/httpClient'
import type { Profile, UserRole } from '@/entities/profile/types'

interface ProfilePage {
  items: Profile[]
  page: number
  page_size: number
  total: number
  total_pages: number
  has_previous: boolean
  has_next: boolean
}

interface ListProfilesParams {
  role?: UserRole
  active?: boolean
  query?: string
  page: number
  pageSize: number
  signal?: AbortSignal
}

const ASSIGNABLE_ROLE_MAP: Record<Exclude<UserRole, 'pendente'>, string> = {
  coordenador: 'coordenador',
  recepcao: 'recepcao',
  instrutor: 'instrutor',
  consulta: 'consulta',
}

export function listProfiles({ role, active, query, page, pageSize, signal }: ListProfilesParams) {
  const params = new URLSearchParams()
  if (role) params.set('role', role)
  if (active !== undefined) params.set('active', String(active))
  if (query) params.set('query', query)
  params.set('page', String(page))
  params.set('page_size', String(pageSize))
  return httpClient.get<ProfilePage>(`/api/v1/profiles?${params.toString()}`, signal)
}

export function changeProfileRole(
  profileId: string,
  payload: { expected_updated_at: string; role: Exclude<UserRole, 'pendente'>; reason: string },
) {
  return httpClient.post<Profile>(`/api/v1/profiles/${profileId}/role`, {
    ...payload,
    role: ASSIGNABLE_ROLE_MAP[payload.role],
  })
}

export function changeProfileActivation(
  profileId: string,
  action: 'activate' | 'deactivate',
  payload: { expected_updated_at: string; reason: string },
) {
  return httpClient.post<Profile>(`/api/v1/profiles/${profileId}/${action}`, payload)
}
