import { Check, Loader2, MailPlus, Search, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { changeProfileActivation, changeProfileRole, generateInviteLink, listProfiles } from '@/features/profiles/api'
import type { Profile, UserRole } from '@/entities/profile/types'
import { ROLE_LABELS } from '@/entities/profile/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { useDebouncedValue } from '@/shared/lib/useDebouncedValue'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageFrame } from '@/shared/ui/PageFrame'
import { MetricCard } from '@/shared/ui/MetricCard'

const ASSIGNABLE_ROLES: Exclude<UserRole, 'pendente'>[] = [
  'coordenador',
  'recepcao',
  'instrutor',
  'consulta',
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
  const [inviteOpen, setInviteOpen] = useState(false)

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
    <PageFrame eyebrow="Acesso e responsabilidades" title="Equipe" description="Administre quem pode operar cada parte do Instituto Livre Acesso." actions={<Button onClick={() => setInviteOpen((value) => !value)}><MailPlus className="h-4 w-4" />{inviteOpen ? 'Fechar convite' : 'Convidar membro'}</Button>}>
      {inviteOpen && <InviteForm onSent={() => setInviteOpen(false)} />}
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
          <div className="liquid-glass flex flex-col items-center gap-3 rounded-2xl p-12 text-center">
            <ShieldCheck className="h-6 w-6 text-white/40" aria-hidden="true" />
            <p className="text-sm text-white/55">Nenhuma conta encontrada para esta busca.</p>
          </div>
        )}
        {!loading &&
          profiles?.map((profile) => (
            <ProfileCard key={profile.id} profile={profile} onChanged={reload} />
          ))}
      </div>
    </PageFrame>
  )
}

function InviteForm({ onSent }: { onSent: () => void }) {
  const [fullName, setFullName] = useState(''); const [email, setEmail] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null); const [link, setLink] = useState<string | null>(null); const [copied, setCopied] = useState(false)
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(null); setCopied(false); try { const result = await generateInviteLink({ full_name: fullName, email }); setLink(result.action_link) } catch (caught) { setError(friendlyMessage(caught)) } finally { setBusy(false) } }
  async function copyLink() { if (!link) return; await navigator.clipboard.writeText(link); setCopied(true); window.setTimeout(() => setCopied(false), 2200) }
  return <form onSubmit={submit} className="mb-6 border border-brand-green/40 bg-brand-green/[.04] p-5"><div className="grid gap-4 md:grid-cols-2"><Input label="Nome completo" required minLength={3} value={fullName} onChange={(event) => setFullName(event.target.value)} /><Input label="E-mail institucional" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></div><p className="mt-3 text-xs text-white/45">Gere um link para a pessoa definir a própria senha. O acesso começa pendente.</p>{error && <p className="mt-3 text-sm text-danger">{error}</p>}{link && <div className="mt-4 border border-brand-green/30 p-3"><p className="text-xs text-brand-green">Link gerado — compartilhe somente com a pessoa convidada.</p><input readOnly value={link} className="mt-2 w-full border border-white/15 bg-black px-3 py-2 text-xs text-white" /><button type="button" className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-brand-green hover:text-white" onClick={() => void copyLink()}>{copied && <Check className="h-3.5 w-3.5" />}{copied ? 'Link copiado' : 'Copiar link'}</button></div>}<div className="mt-4 flex flex-wrap gap-3"><Button type="submit" loading={busy}>Gerar link</Button><Button type="button" variant="secondary" onClick={onSent}>Fechar</Button></div></form>
}

function ProfileCard({ profile, onChanged }: { profile: Profile; onChanged: () => void }) {
  const [role, setRole] = useState<Exclude<UserRole, 'pendente'>>(
    profile.role === 'pendente' ? 'consulta' : profile.role,
  )
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleRoleChange() {
    if (reason.trim().length < 10) {
      setError('Informe um motivo com pelo menos 10 caracteres.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await changeProfileRole(profile.id, {
        expected_updated_at: profile.updated_at,
        role,
        reason,
      })
      setReason('')
      onChanged()
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  async function handleActivation() {
    if (reason.trim().length < 10) {
      setError('Informe um motivo com pelo menos 10 caracteres.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await changeProfileActivation(profile.id, profile.active ? 'deactivate' : 'activate', {
        expected_updated_at: profile.updated_at,
        reason,
      })
      setReason('')
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
        </div>
        <StatusBadge
          label={profile.active ? 'Ativo' : 'Inativo'}
          tone={profile.active ? 'success' : 'neutral'}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`role-${profile.id}`} className="text-xs font-medium text-white/60">
            Novo papel
          </label>
          <select
            id={`role-${profile.id}`}
            value={role}
            onChange={(event) => setRole(event.target.value as Exclude<UserRole, 'pendente'>)}
            disabled={busy}
            className="h-10 rounded-lg border border-white/10 bg-white/5 px-3 text-sm text-white outline-none transition focus:border-brand-green"
          >
            {ASSIGNABLE_ROLES.map((value) => (
              <option key={value} value={value} className="bg-surface">
                {ROLE_LABELS[value]}
              </option>
            ))}
          </select>
        </div>
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
      </div>

      <div className="mt-3">
        <Input
          label="Motivo (para qualquer ação acima)"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          disabled={busy}
          hint="Entre 10 e 500 caracteres."
        />
      </div>
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  )
}
