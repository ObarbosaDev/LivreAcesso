import { CalendarDays, ChevronLeft, ChevronRight, MapPin, Plus, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '@/app/providers/AuthProvider'
import { cancelAgendaEvent, createAgendaEvent, listAgenda } from '@/features/agenda/api'
import type { AgendaEvent, AgendaEventType } from '@/entities/agenda/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { EmptyState } from '@/shared/ui/EmptyState'
import { Input } from '@/shared/ui/Input'
import { PageFrame } from '@/shared/ui/PageFrame'
import { Select } from '@/shared/ui/Select'

const labels: Record<AgendaEventType, string> = { turma: 'Turma', reuniao: 'Reunião', atendimento: 'Atendimento', evento: 'Evento', bloqueio: 'Bloqueio', outro: 'Outro' }
function monthRange(cursor: Date) { const start = new Date(cursor.getFullYear(), cursor.getMonth(), 1); const end = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1); return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) } }
function monthLabel(cursor: Date) { return new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' }).format(cursor) }

export function AgendaPage() {
  usePageTitle('Agenda')
  const { profile } = useAuth()
  const canManageAgenda = profile?.capabilities.includes('agenda:manage') ?? false
  const [cursor, setCursor] = useState(() => { const now = new Date(); return new Date(now.getFullYear(), now.getMonth(), 1) })
  const range = useMemo(() => monthRange(cursor), [cursor]); const [events, setEvents] = useState<AgendaEvent[]>([]); const [loading, setLoading] = useState(true); const [open, setOpen] = useState(false); const [error, setError] = useState<string | null>(null)
  const [cancelingEventId, setCancelingEventId] = useState<string | null>(null)
  const reload = useCallback(async () => { setLoading(true); try { setEvents(await listAgenda(range.start, range.end)); setError(null) } catch (caught) { setError(friendlyMessage(caught)) } finally { setLoading(false) } }, [range.end, range.start])
  useEffect(() => { void reload() // eslint-disable-line react-hooks/set-state-in-effect
  }, [reload])
  async function cancelEvent(item: AgendaEvent, reason: string) { try { await cancelAgendaEvent(item.id, item.updated_at, reason); setCancelingEventId(null); await reload() } catch (caught) { setError(friendlyMessage(caught)) } }
  function shiftMonth(amount: number) { setCursor((current) => new Date(current.getFullYear(), current.getMonth() + amount, 1)) }
  return <PageFrame eyebrow="Rotina do instituto" title="Agenda" description="Horários de turma, reuniões, atendimentos e compromissos em um único lugar." actions={canManageAgenda && <Button onClick={() => setOpen((value) => !value)}><Plus className="h-4 w-4" />{open ? 'Fechar' : 'Novo compromisso'}</Button>}>
    {open && canManageAgenda && <AgendaForm onSaved={() => { setOpen(false); void reload() }} />}
    {error && <p className="border border-danger/40 p-4 text-sm text-danger">{error}</p>}
    <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-y border-white/10 py-4"><div><p className="text-xs uppercase tracking-[0.14em] text-white/40">Período</p><p className="mt-1 font-display text-sm capitalize text-white">{monthLabel(cursor)}</p></div><div className="flex items-center gap-2"><Button variant="secondary" aria-label="Mês anterior" onClick={() => shiftMonth(-1)}><ChevronLeft className="h-4 w-4" /></Button><Button variant="secondary" aria-label="Próximo mês" onClick={() => shiftMonth(1)}><ChevronRight className="h-4 w-4" /></Button><Button variant="secondary" onClick={() => void reload()}><RefreshCw className="h-4 w-4" /> Atualizar</Button></div></div>
    {loading ? (
      <p className="py-12 text-sm text-white/45">Carregando agenda…</p>
    ) : events.length === 0 ? (
      <div className="mt-6">
        <EmptyState
          icon={CalendarDays}
          title="Nenhum compromisso neste período"
          description="Cadastre uma reunião, atendimento ou horário para começar a organizar a rotina."
        />
      </div>
    ) : (
      <div className="mt-6 divide-y divide-white/10 border-y border-white/10">
        {events.map((event, index) => (
          <article key={event.id} className="py-5">
            <div className="grid gap-3 md:grid-cols-[5rem_1fr_auto] md:items-center">
              <span className="font-display text-xs text-brand-green/70">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="font-display text-sm font-semibold text-white">{event.title}</h2>
                  <span className="text-[10px] uppercase tracking-[0.12em] text-brand-green">{labels[event.event_type]}</span>
                </div>
                <p className="mt-2 text-xs text-white/45">{event.description ?? 'Sem descrição registrada.'}</p>
                {event.location && (
                  <p className="mt-2 flex items-center gap-1.5 text-xs text-white/40">
                    <MapPin className="h-3.5 w-3.5" />
                    {event.location}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-4">
                <p className="font-display text-xs text-white/55">{new Date(event.starts_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</p>
                {canManageAgenda && <button type="button" onClick={() => setCancelingEventId(event.id)} className="text-xs text-danger/70 hover:text-danger">Cancelar</button>}
              </div>
            </div>
            {cancelingEventId === event.id && (
              <AgendaCancelForm
                onCancel={() => setCancelingEventId(null)}
                onConfirm={(reason) => cancelEvent(event, reason)}
              />
            )}
          </article>
        ))}
      </div>
    )}
  </PageFrame>
}

function AgendaCancelForm({
  onCancel,
  onConfirm,
}: {
  onCancel: () => void
  onConfirm: (reason: string) => Promise<void>
}) {
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (reason.trim().length < 10) {
      setError('Informe um motivo com pelo menos 10 caracteres.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await onConfirm(reason)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 border-t border-white/10 pt-4">
      <Input
        label="Motivo do cancelamento"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        disabled={submitting}
        hint="Pelo menos 10 caracteres."
      />
      {error && <p className="text-sm text-danger">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" variant="danger" loading={submitting}>
          Confirmar cancelamento
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={submitting}>
          Voltar
        </Button>
      </div>
    </form>
  )
}

function AgendaForm({ onSaved }: { onSaved: () => void }) { const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null); const [form, setForm] = useState({ title: '', description: '', event_type: 'reuniao' as AgendaEventType, starts_at: '', ends_at: '', all_day: false, location: '' }); function field(key: string, value: string | boolean) { setForm((current) => ({ ...current, [key]: value })) } async function submit(event: FormEvent) { event.preventDefault(); setSaving(true); try { await createAgendaEvent({ ...form, starts_at: new Date(form.starts_at).toISOString(), ends_at: new Date(form.ends_at).toISOString(), location: form.location.trim() || undefined, description: form.description.trim() || undefined }); onSaved() } catch (caught) { setError(friendlyMessage(caught)) } finally { setSaving(false) } } return <form onSubmit={submit} className="mt-6 border border-brand-green/40 bg-brand-green/[.03] p-5"><div className="grid gap-4 md:grid-cols-2"><Input label="Título" required value={form.title} onChange={(event) => field('title', event.target.value)} /><Input label="Local" value={form.location} onChange={(event) => field('location', event.target.value)} /><Input label="Início" type="datetime-local" required value={form.starts_at} onChange={(event) => field('starts_at', event.target.value)} /><Input label="Fim" type="datetime-local" required value={form.ends_at} onChange={(event) => field('ends_at', event.target.value)} /></div><div className="mt-4"><Select label="Tipo" value={form.event_type} onChange={(event) => field('event_type', event.target.value)} options={Object.entries(labels).map(([value, label]) => ({ value, label }))} /></div><label className="mt-4 block text-xs text-white/55">Descrição<textarea className="mt-2 min-h-24 w-full border border-white/15 bg-black p-3 text-sm text-white" value={form.description} onChange={(event) => field('description', event.target.value)} /></label>{error && <p className="mt-3 text-sm text-danger">{error}</p>}<Button type="submit" loading={saving} className="mt-4">Salvar compromisso</Button></form> }
