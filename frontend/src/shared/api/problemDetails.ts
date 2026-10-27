/** Formato de erro usado por toda a API (application/problem+json). */
export interface ProblemFieldError {
  field: string
  code: string
  message: string
}

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail: string
  code: string
  request_id: string
  errors?: ProblemFieldError[]
}

/** Erro de API tipado; carrega o Problem Detail original para a interface decidir a mensagem. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string
  readonly fieldErrors: ProblemFieldError[]

  constructor(problem: ProblemDetail) {
    super(problem.detail || problem.title)
    this.name = 'ApiError'
    this.status = problem.status
    this.code = problem.code
    this.requestId = problem.request_id
    this.fieldErrors = problem.errors ?? []
  }
}

/**
 * Traduz códigos estáveis do backend em mensagens acolhedoras. Nunca repete
 * SQL, stack trace ou texto bruto do PostgreSQL — a pessoa só vê o que ajuda
 * a decidir o próximo passo.
 */
export function friendlyMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'authentication_required':
        return 'Sua sessão expirou. Entre novamente.'
      case 'forbidden':
        return 'Você não tem permissão para realizar esta ação.'
      case 'duplicate_cpf':
        return 'Este CPF já pertence a um cadastro existente.'
      case 'duplicate_enrollment':
        return 'Este estudante já está matriculado nesta turma.'
      case 'class_capacity_reached':
        return 'A turma ficou sem vagas.'
      case 'student_version_conflict':
      case 'guardian_version_conflict':
      case 'enrollment_version_conflict':
      case 'profile_version_conflict':
        return 'Este registro foi alterado por outra pessoa. Atualize a tela antes de tentar novamente.'
      case 'student_not_found':
      case 'class_not_found':
      case 'enrollment_not_found':
      case 'profile_not_found':
        return 'Não encontramos este registro. Ele pode ter sido removido.'
      default:
        return error.message || 'Não foi possível concluir a ação.'
    }
  }
  if (error instanceof Error && error.name === 'AbortError') {
    return 'A solicitação demorou demais. Tente novamente.'
  }
  return 'O serviço está indisponível no momento. Tente novamente em instantes.'
}
