import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import { publicEnv } from '@/shared/config/env'

/**
 * `null` quando a configuração pública está incompleta. Nunca criamos um
 * cliente com URL/chave vazias: isso produziria erros confusos em vez da
 * mensagem clara que a tela de login mostra quando falta configuração.
 */
export const supabase: SupabaseClient | null = publicEnv
  ? createClient(publicEnv.supabaseUrl, publicEnv.supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        // Precisa ficar ligado: é assim que a sessão de recuperação de senha
        // chega do link enviado por e-mail até a tela de redefinição.
        detectSessionInUrl: true,
      },
    })
  : null
