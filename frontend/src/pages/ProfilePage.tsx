import { CalendarDays, Check, Copy, LockKeyhole, ShieldCheck, User } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'

import { useAuth } from '@/app/providers/AuthProvider'
import { ROLE_LABELS, type Capability } from '@/entities/profile/types'
import { httpClient } from '@/shared/api/httpClient'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { PageFrame } from '@/shared/ui/PageFrame'

const CAPABILITY_LABELS: Record<Capability, string> = {
  'profiles:read': 'Consultar equipe', 'profiles:manage': 'Gerenciar equipe',
  'students:list': 'Listar estudantes', 'students:read': 'Ver dados de estudante',
  'students:create': 'Cadastrar estudante', 'students:update': 'Atualizar estudante',
  'students:change-status': 'Alterar status do estudante', 'classes:list': 'Listar turmas',
  'classes:read': 'Ver detalhes de turma', 'classes:manage': 'Gerenciar turmas',
}

export function ProfilePage() {
  usePageTitle('Meu perfil')
  const { profile, reloadProfile } = useAuth()
  const [fullName, setFullName] = useState(profile?.full_name ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)
  if (!profile) return null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault(); if (saving) return
    setError(null); setSaved(false); setSaving(true)
    try { await httpClient.put('/api/v1/me', { expected_updated_at: profile.updated_at, full_name: fullName }); await reloadProfile(); setSaved(true) }
    catch (caught) { setError(friendlyMessage(caught)) } finally { setSaving(false) }
  }

  async function copyId() { await navigator.clipboard.writeText(profile.id); setCopied(true); window.setTimeout(() => setCopied(false), 1800) }

  return <PageFrame eyebrow="Conta e preferências" title="Meu perfil" description="Identidade, papel e permissões efetivas dentro do sistema.">
    <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
      <section className="liquid-glass p-6">
        <div className="flex items-start justify-between gap-4 border-b border-white/10 pb-5"><div className="flex items-center gap-3"><span className="flex h-12 w-12 items-center justify-center bg-brand-green/15"><User className="h-5 w-5 text-brand-green" /></span><div><p className="font-semibold text-white">{profile.full_name}</p><button type="button" onClick={() => void copyId()} className="mt-1 inline-flex items-center gap-1.5 text-xs text-white/45 hover:text-brand-green"><Copy className="h-3 w-3" />{copied ? 'ID copiado' : `ID ${profile.id.slice(0, 8)}...`}</button></div></div><span className="flex items-center gap-1.5 text-xs text-brand-green"><span className="h-2 w-2 bg-brand-green" />{profile.active ? 'Ativo' : 'Inativo'}</span></div>
        <dl className="mt-6 space-y-4 text-sm"><div className="flex justify-between gap-4"><dt className="text-white/45">Papel operacional</dt><dd className="font-semibold text-white">{ROLE_LABELS[profile.role]}</dd></div><div className="flex justify-between gap-4"><dt className="text-white/45">Conta criada</dt><dd className="text-white">{formatDate(profile.created_at)}</dd></div><div className="flex justify-between gap-4"><dt className="text-white/45">Atualização</dt><dd className="text-white">{formatDate(profile.updated_at)}</dd></div></dl>
        <div className="mt-7 border-t border-white/10 pt-5"><p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-white/40"><LockKeyhole className="h-4 w-4" /> Controle de acesso</p><p className="mt-3 text-sm leading-6 text-white/50">Seu papel e seu status são administrados pela coordenação. Aqui você corrige apenas seu nome.</p></div>
      </section>
      <section className="liquid-glass p-6"><div className="flex items-start justify-between border-b border-white/10 pb-5"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/40">Dados editáveis</p><h2 className="mt-2 font-display text-xl font-semibold text-white">Identificação</h2></div><ShieldCheck className="h-5 w-5 text-brand-green" /></div><form onSubmit={handleSubmit} className="mt-6 flex max-w-xl flex-col gap-4"><Input label="Nome completo" value={fullName} onChange={(event) => setFullName(event.target.value)} disabled={saving} />{error && <p role="alert" className="text-sm text-danger">{error}</p>}{saved && <p className="text-sm text-brand-green">Nome atualizado.</p>}<Button type="submit" loading={saving} className="w-full sm:w-auto">{saving ? 'Salvando…' : 'Salvar alterações'}</Button></form></section>
    </div>
    <section className="liquid-glass mt-6 p-6"><div className="flex items-center gap-3"><CalendarDays className="h-5 w-5 text-brand-green" /><div><h2 className="font-display text-xl font-semibold text-white">Permissões efetivas</h2><p className="mt-1 text-sm text-white/45">Ações liberadas para o seu papel atual.</p></div></div>{profile.capabilities.length > 0 ? <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{profile.capabilities.map((capability) => <div key={capability} className="flex items-center gap-3 border border-white/10 bg-white/[.02] px-3 py-3 text-sm text-white/70"><span className="flex h-6 w-6 items-center justify-center bg-brand-green/15 text-brand-green"><Check className="h-3.5 w-3.5" /></span>{CAPABILITY_LABELS[capability]}</div>)}</div> : <p className="mt-6 border border-dashed border-white/15 p-5 text-sm text-white/45">Nenhuma permissão operacional foi atribuída a esta conta.</p>}</section>
  </PageFrame>
}

function formatDate(value: string) { return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium' }).format(new Date(value)) }
