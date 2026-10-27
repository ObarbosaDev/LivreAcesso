/**
 * Configuração pública do frontend, lida das variáveis VITE_* do Vite.
 *
 * Todas essas variáveis entram no bundle público do navegador. Por isso
 * nenhuma delas pode ser um segredo: a URL do Supabase e a chave
 * "publishable" são seguras por design (a autorização real continua no
 * backend e nas RPCs), mas nunca deve existir aqui uma service_role key.
 */

interface PublicEnv {
  supabaseUrl: string
  supabaseAnonKey: string
  apiBaseUrl: string
}

function readEnv(name: string): string | undefined {
  const value = import.meta.env[name as keyof ImportMetaEnv]
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined
}

function loadPublicEnv(): PublicEnv | null {
  const supabaseUrl = readEnv('VITE_SUPABASE_URL')
  const supabaseAnonKey = readEnv('VITE_SUPABASE_PUBLISHABLE_KEY')
  const apiBaseUrl = readEnv('VITE_API_BASE_URL')

  if (!supabaseUrl || !supabaseAnonKey || !apiBaseUrl) {
    return null
  }
  return { supabaseUrl, supabaseAnonKey, apiBaseUrl }
}

/**
 * `null` quando a configuração está incompleta. A tela de login trata esse
 * caso mostrando uma mensagem segura em vez de travar a aplicação em branco,
 * espelhando a regra "falha fechada" já adotada no backend.
 */
export const publicEnv = loadPublicEnv()
