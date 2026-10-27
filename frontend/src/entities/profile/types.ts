/** Espelha ProfileOutput do backend (backend/app/modules/identity/application/dtos.py). */
export type UserRole = 'pendente' | 'coordenador' | 'recepcao' | 'instrutor' | 'consulta'

export type Capability =
  | 'profiles:read'
  | 'profiles:manage'
  | 'students:list'
  | 'students:read'
  | 'students:create'
  | 'students:update'
  | 'students:change-status'
  | 'classes:list'
  | 'classes:read'
  | 'classes:manage'

export interface Profile {
  id: string
  full_name: string
  role: UserRole
  active: boolean
  capabilities: Capability[]
  created_at: string
  updated_at: string
}

export const ROLE_LABELS: Record<UserRole, string> = {
  pendente: 'Pendente',
  coordenador: 'Coordenação',
  recepcao: 'Recepção',
  instrutor: 'Instrutor',
  consulta: 'Consulta',
}
