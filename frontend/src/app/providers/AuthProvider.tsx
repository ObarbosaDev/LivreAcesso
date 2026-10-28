import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'

import { httpClient } from '@/shared/api/httpClient'
import { supabase } from '@/shared/api/supabaseClient'
import type { Profile } from '@/entities/profile/types'

type AuthStatus = 'loading' | 'signed-out' | 'signed-in' | 'config-missing'

interface AuthContextValue {
  status: AuthStatus
  session: Session | null
  profile: Profile | null
  profileError: string | null
  /** Sessão temporária criada pelo link de "esqueci minha senha", válida só para trocar a senha. */
  isPasswordRecovery: boolean
  signIn: (email: string, password: string) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
  reloadProfile: () => Promise<void>
  requestPasswordReset: (email: string) => Promise<{ error: string | null }>
  updatePassword: (password: string) => Promise<{ error: string | null }>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [status, setStatus] = useState<AuthStatus>(supabase ? 'loading' : 'config-missing')
  const [isPasswordRecovery, setIsPasswordRecovery] = useState(false)

  const loadProfile = useCallback(async () => {
    try {
      const current = await httpClient.get<Profile>('/api/v1/me')
      setProfile(current)
      setProfileError(null)
    } catch {
      // Sessão válida no Supabase, mas sem perfil operacional correspondente
      // ainda é possível logo após o primeiro login. A tela trata isso como
      // "sem acesso" em vez de travar silenciosamente.
      setProfile(null)
      setProfileError('Não foi possível carregar seu perfil operacional.')
    }
  }, [])

  useEffect(() => {
    if (!supabase) {
      return
    }

    let active = true

    // O perfil operacional é carregado aqui, dentro da própria reação à
    // mudança de sessão, e não em um segundo efeito disparado por `status`:
    // evita o cascading render de um setState síncrono no corpo do efeito e
    // garante que toda troca de sessão (login, refresh, logout) já chega com
    // o perfil atualizado.
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session)
      setStatus(data.session ? 'signed-in' : 'signed-out')
      if (data.session) {
        void loadProfile()
      }
    })

    const { data: subscription } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (!active) return
      setSession(nextSession)
      setStatus(nextSession ? 'signed-in' : 'signed-out')
      if (event === 'PASSWORD_RECOVERY') {
        // Sessão de uso único vinda do link de e-mail: não deve liberar o
        // sistema, só a tela de redefinição de senha.
        setIsPasswordRecovery(true)
        return
      }
      if (nextSession) {
        void loadProfile()
      } else {
        setProfile(null)
      }
    })

    return () => {
      active = false
      subscription.subscription.unsubscribe()
    }
  }, [loadProfile])

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) {
      return { error: 'Configuração indisponível no momento.' }
    }
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) {
      // Nunca confirmamos se o e-mail existe: a mesma mensagem cobre usuário
      // inexistente e senha incorreta, evitando enumeração de contas.
      return { error: 'E-mail ou senha incorretos.' }
    }
    return { error: null }
  }, [])

  const signOut = useCallback(async () => {
    if (!supabase) return
    await supabase.auth.signOut()
    setProfile(null)
    setIsPasswordRecovery(false)
  }, [])

  const requestPasswordReset = useCallback(async (email: string) => {
    if (!supabase) {
      return { error: 'Configuração indisponível no momento.' }
    }
    await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/redefinir-senha`,
    })
    // Mesma resposta sempre: confirmar que o e-mail enviado existe permitiria
    // descobrir contas cadastradas por tentativa e erro.
    return { error: null }
  }, [])

  const updatePassword = useCallback(async (password: string) => {
    if (!supabase) {
      return { error: 'Configuração indisponível no momento.' }
    }
    const { error } = await supabase.auth.updateUser({ password })
    if (error) {
      return { error: 'Não foi possível definir a nova senha. Tente novamente.' }
    }
    setIsPasswordRecovery(false)
    return { error: null }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      session,
      profile,
      profileError,
      isPasswordRecovery,
      signIn,
      signOut,
      reloadProfile: loadProfile,
      requestPasswordReset,
      updatePassword,
    }),
    [
      status,
      session,
      profile,
      profileError,
      isPasswordRecovery,
      signIn,
      signOut,
      loadProfile,
      requestPasswordReset,
      updatePassword,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// O hook precisa compartilhar o mesmo contexto privado do provider; manter os dois
// exports aqui evita duplicar a instância de autenticação entre módulos.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth precisa estar dentro de AuthProvider.')
  }
  return context
}
