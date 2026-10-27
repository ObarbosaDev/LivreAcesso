/** Espelha os contratos de responsáveis (backend/app/modules/students/application/dtos.py). */
export const GUARDIAN_RELATIONSHIPS = [
  'contato_responsavel',
  'responsavel_legal',
  'pai_ou_mae',
  'contato_emergencia',
  'proprio',
  'outro',
] as const
export type GuardianRelationship = (typeof GUARDIAN_RELATIONSHIPS)[number]

export const GUARDIAN_RELATIONSHIP_LABELS: Record<GuardianRelationship, string> = {
  contato_responsavel: 'Contato responsável',
  responsavel_legal: 'Responsável legal',
  pai_ou_mae: 'Pai ou mãe',
  contato_emergencia: 'Contato de emergência',
  proprio: 'O próprio participante',
  outro: 'Outro',
}

export interface GuardianListItem {
  id: string
  full_name: string
  phone_masked: string
  email_masked: string | null
  relationship: GuardianRelationship
  is_primary: boolean
  receives_communications: boolean
  linked_at: string
  guardian_updated_at: string
}

export interface GuardianListResult {
  student_id: string
  student_updated_at: string
  items: GuardianListItem[]
}

export interface GuardianDetail {
  student_id: string
  student_updated_at: string
  id: string
  full_name: string
  phone: string
  email: string | null
  relationship: GuardianRelationship
  is_primary: boolean
  receives_communications: boolean
  linked_at: string
  guardian_updated_at: string
}
