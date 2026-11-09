import { Loader2, Search, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'

import { changeProfileActivation, changeProfileRole, listProfiles } from '@/features/profiles/api'
import type { Profile, UserRole } from '@/entities/profile/types'
import { ROLE_LABELS } from '@/entities/profile/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Input } from '@/shared/ui/Input'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageFrame } from '@/shared/ui/PageFrame'
import { MetricCard } from '@/shared/ui/MetricCard'
import { Select } from '@/shared/ui/Select'

const ASSIGNABLE_ROLES: Exclude<UserRole, 'pendente'>[] = [
  'coordenador',
  'recepcao',
  'instrutor',
]

const PAGE_SIZE = 25

export function ProfilesAdminPage() {
  usePageTitle('Equipe')

  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query)
  const [profiles, setProfiles] = useState<Profile[] | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const result = await listProfiles({
        query: debouncedQuery.trim().length >= 2 ? debouncedQuery.trim() : undefined,
        page: 1,
        pageSize: PAGE_SIZE,
      })
      setProfiles(result.items)
      setTotal(result.total)
      setError(null)
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca inicial ao entrar ou trocar o filtro
    setLoading(true)
    void reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery])

  return (
    <PageFrame eyebrow="Acesso e responsabilidades" title="Equipe" description="Administre quem pode operar cada parte do Instituto Livre Acesso.">
      <p className="mt-2 text-sm text-white/55">
        {profiles ? `${total} ${total === 1 ? 'conta' : 'contas'}` : 'Carregando…'} · administre papel
        e ativação de cada conta.
      </p>

      <div className="mb-6 grid gap-4 md:grid-cols-3"><MetricCard label="Contas encontradas" value={total} icon={ShieldCheck} /><MetricCard label="Ativas" value={profiles?.filter((item) => item.active).length ?? '—'} icon={ShieldCheck} tone="green" /><MetricCard label="Pendentes" value={profiles?.filter((item) => item.role === 'pendente').length ?? '—'} icon={ShieldCheck} tone="amber" /></div>
      <div className="liquid-glass rounded-3xl p-4"><Input
        label="Pesquisar"
        placeholder="Buscar por nome…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        icon={<Search className="h-4 w-4" aria-hidden="true" />}
        className="max-w-md"
      /></div>

      <div className="mt-6 flex flex-col gap-3">
        {loading && (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-white/50">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Carregando equipe…
          </div>
        )}
        {error && <p className="text-sm text-danger">{error}</p>}
        {!loading && !error && profiles?.length === 0 && (
          <EmptyState
            icon={ShieldCheck}
            title="Nenhuma conta encontrada"
            description="Tente outro termo de busca. Para ganhar acesso, a pessoa pede pelo link /cadastro."
          />
        )}
        {!loading &&
          profiles?.map((profile) => (
            <ProfileCard key={profile.id} profile={profile} onChanged={reload} />
          ))}
      </div>
    </PageFrame>
  )
}

function ProfileCard({ profile, onChanged }: { profile: Profile; onChanged: () => void }) {
  const fallbackRole = (candidate: UserRole | null): Exclude<UserRole, 'pendente'> =>
    candidate && candidate !== 'pendente' ? candidate : 'instrutor'
  const [role, setRole] = useState<Exclude<UserRole, 'pendente'>>(
    profile.role === 'pendente' ? fallbackRole(profile.requested_role) : fallbackRole(profile.role),
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isPending = profile.role === 'pendente'

  async function handleAccept() {
    setBusy(true)
    setError(null)
    try {
      const afterRole = await changeProfileRole(profile.id, {
        expected_updated_at: profile.updated_at,
        role,
      })
      await changeProfileActivation(profile.id, 'activate', {
        expected_updated_at: afterRole.updated_at,
      })
      onChanged()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function handleRoleChange() {
    setBusy(true)
    setError(null)
    try {
      await changeProfileRole(profile.id, { expected_updated_at: profile.updated_at, role })
      onChanged()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function handleActivation() {
    setBusy(true)
    setError(null)
    try {
      await changeProfileActivation(profile.id, profile.active ? 'deactivate' : 'activate', {
        expected_updated_at: profile.updated_at,
      })
      onChanged()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="liquid-glass rounded-2xl p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-white">{profile.full_name}</p>
          <p className="text-xs text-white/50">{ROLE_LABELS[profile.role]}</p>
          {isPending && profile.requested_role && (
            <p className="mt-1 text-xs text-brand-green">
              Pediu acesso como {ROLE_LABELS[profile.requested_role]}
            </p>
          )}
        </div>
        <StatusBadge
          label={profile.active ? 'Ativo' : 'Inativo'}
          tone={profile.active ? 'success' : 'neutral'}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <Select
          label={isPending ? 'Papel' : 'Alterar papel para'}
          id={`role-${profile.id}`}
          value={role}
          onChange={(event) => setRole(event.target.value as Exclude<UserRole, 'pendente'>)}
          disabled={busy}
          className="h-10"
          options={ASSIGNABLE_ROLES.map((value) => ({ value, label: ROLE_LABELS[value] }))}
        />
        {isPending ? (
          <Button onClick={handleAccept} disabled={busy} className="h-10">
            Aceitar pedido
          </Button>
        ) : (
          <>
            <Button variant="secondary" onClick={handleRoleChange} disabled={busy} className="h-10">
              Alterar papel
            </Button>
            <Button
              variant={profile.active ? 'danger' : 'primary'}
              onClick={handleActivation}
              disabled={busy}
              className="h-10"
            >
              {profile.active ? 'Desativar' : 'Ativar'}
            </Button>
          </>
        )}
      </div>

      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  )
}
