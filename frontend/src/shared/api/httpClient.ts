import { publicEnv } from '@/shared/config/env'
import { supabase } from '@/shared/api/supabaseClient'
import { ApiError, type ProblemDetail } from '@/shared/api/problemDetails'

const REQUEST_TIMEOUT_MS = 15_000

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
}

/**
 * As páginas nunca chamam fetch diretamente: este cliente centraliza base
 * URL, token da sessão Supabase, timeout e a conversão de erros
 * application/problem+json em ApiError, para que cada tela só decida o que
 * mostrar, não como pedir.
 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!publicEnv) {
    throw new Error('Configuração pública ausente.')
  }

  const session = supabase ? (await supabase.auth.getSession()).data.session : null
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (session?.access_token) {
    headers.Authorization = `Bearer ${session.access_token}`
  }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const timeoutController = new AbortController()
  const timeoutId = setTimeout(() => timeoutController.abort(), REQUEST_TIMEOUT_MS)
  const signal = options.signal
    ? mergeSignals(options.signal, timeoutController.signal)
    : timeoutController.signal

  let response: Response
  try {
    response = await fetch(`${publicEnv.apiBaseUrl}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal,
    })
  } finally {
    clearTimeout(timeoutId)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    if (payload && typeof payload === 'object' && 'code' in payload) {
      throw new ApiError(payload as ProblemDetail)
    }
    throw new ApiError({
      type: 'about:blank',
      title: 'Erro inesperado',
      status: response.status,
      detail: 'O serviço retornou uma resposta inesperada.',
      code: 'unexpected_response',
      request_id: response.headers.get('X-Request-ID') ?? '',
    })
  }

  return payload as T
}

function mergeSignals(a: AbortSignal, b: AbortSignal): AbortSignal {
  const controller = new AbortController()
  const abort = () => controller.abort()
  a.addEventListener('abort', abort)
  b.addEventListener('abort', abort)
  return controller.signal
}

export const httpClient = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { method: 'GET', signal }),
  post: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: 'POST', body, signal }),
  put: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: 'PUT', body, signal }),
}
