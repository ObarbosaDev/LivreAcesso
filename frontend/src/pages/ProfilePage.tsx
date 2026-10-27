import { User } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { useAuth } from '@/app/providers/AuthProvider'
import { ROLE_LABELS } from '@/entities/profile/types'
import { httpClient } from '@/shared/api/httpClient'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { PageFrame } from '@/shared/ui/PageFrame'

/** Corrige só o próprio nome: papel, ativação e capacidades continuam exclusivos da coordenação. */
export function ProfilePage() {
  usePageTitle('Meu perfil')
  const { profile, reloadProfile } = useAuth()

  const [fullName, setFullName] = useState(profile?.full_name ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  if (!profile) return null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (saving) return
    setError(null)
    setSaved(false)
    setSaving(true)

    try {
      await httpClient.put('/api/v1/me', {
        expected_updated_at: profile!.updated_at,
        full_name: fullName,
      })
      await reloadProfile()
      setSaved(true)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <PageFrame eyebrow="Conta e preferências" title="Meu perfil" description="Mantenha seus dados de identificação atualizados no sistema.">
      <p className="mt-2 text-sm text-white/55">
        Papel e ativação são administrados pela coordenação; aqui você corrige só o seu nome.
      </p>

      <div className="liquid-glass mt-8 rounded-2xl p-6">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-green/15">
            <User className="h-5 w-5 text-brand-green" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-medium text-white">{profile.full_name}</p>
            <p className="text-xs text-white/50">{ROLE_LABELS[profile.role]}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <Input
            label="Nome completo"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            disabled={saving}
          />

          {error && (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          )}
          {saved && <p className="text-sm text-brand-green">Nome atualizado.</p>}

          <Button type="submit" loading={saving} className="w-full sm:w-auto">
            {saving ? 'Salvando…' : 'Salvar'}
          </Button>
        </form>
      </div>
    </PageFrame>
  )
}
