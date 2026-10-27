import { ArrowLeft, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createClass, createModality, listModalities } from '@/features/classes/api'
import { listProfiles } from '@/features/profiles/api'
import type { Modality, Weekday } from '@/entities/class/types'
import { WEEKDAYS, WEEKDAY_LABELS } from '@/entities/class/types'
import type { Profile } from '@/entities/profile/types'
import { friendlyMessage } from '@/shared/api/problemDetails'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { PageFrame } from '@/shared/ui/PageFrame'

export function NewClassPage() {
  usePageTitle('Nova turma')
  const navigate = useNavigate()

  const [modalities, setModalities] = useState<Modality[]>([])
  const [modalityId, setModalityId] = useState('')
  const [newModalityName, setNewModalityName] = useState('')
  const [creatingModality, setCreatingModality] = useState(false)

  const [instructors, setInstructors] = useState<Profile[]>([])
  const [selectedInstructors, setSelectedInstructors] = useState<string[]>([])

  const [name, setName] = useState('')
  const [capacity, setCapacity] = useState('20')
  const [location, setLocation] = useState('')
  const [minimumAge, setMinimumAge] = useState('')
  const [maximumAge, setMaximumAge] = useState('')
  const [weekday, setWeekday] = useState<Weekday>('segunda')
  const [startsAt, setStartsAt] = useState('09:00')
  const [endsAt, setEndsAt] = useState('10:00')

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listModalities(true)
      .then((result) => {
        setModalities(result.items)
        if (result.items.length > 0) setModalityId(result.items[0].id)
      })
      .catch(() => {})
    listProfiles({ role: 'instrutor', active: true, page: 1, pageSize: 100 })
      .then((result) => setInstructors(result.items))
      .catch(() => {})
  }, [])

  async function handleCreateModality() {
    if (newModalityName.trim().length < 3) return
    setCreatingModality(true)
    try {
      const modality = await createModality({ name: newModalityName.trim() })
      setModalities((current) => [...current, modality])
      setModalityId(modality.id)
      setNewModalityName('')
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setCreatingModality(false)
    }
  }

  function toggleInstructor(id: string) {
    setSelectedInstructors((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    )
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setError(null)

    if (!modalityId) {
      setError('Escolha ou crie uma modalidade.')
      return
    }
    if (selectedInstructors.length === 0) {
      setError('Selecione ao menos um instrutor.')
      return
    }

    setSubmitting(true)
    try {
      await createClass({
        modality_id: modalityId,
        name,
        capacity: Number(capacity),
        location,
        minimum_age: minimumAge ? Number(minimumAge) : undefined,
        maximum_age: maximumAge ? Number(maximumAge) : undefined,
        schedules: [{ weekday, starts_at: startsAt, ends_at: endsAt }],
        instructor_ids: selectedInstructors,
      })
      navigate('/turmas')
    } catch (caught) {
      setError(friendlyMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <PageFrame eyebrow="Programação" title="Criar turma" description="Monte uma oferta concreta com modalidade, capacidade, horário e equipe responsável.">
      <Link
        to="/turmas"
        className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-white/50 transition hover:text-white"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
        Voltar para turmas
      </Link>

      <p className="mt-2 text-sm text-white/55">
        Cria uma oferta concreta com capacidade, horário e ao menos um instrutor ativo.
      </p>

      <form onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-8">
        <fieldset className="liquid-glass flex flex-col gap-4 rounded-2xl p-6">
          <legend className="px-1 font-display text-sm font-semibold text-white">Modalidade</legend>
          <div className="flex flex-col gap-2">
            <label htmlFor="modality" className="text-sm font-medium text-white">
              Escolher existente
            </label>
            <select
              id="modality"
              value={modalityId}
              onChange={(event) => setModalityId(event.target.value)}
              className="h-12 rounded-xl border border-white/10 bg-white/5 px-4 text-white outline-none transition focus:border-brand-green focus:bg-white/8 focus:ring-4 focus:ring-brand-green/15"
            >
              {modalities.length === 0 && (
                <option value="" className="bg-surface">
                  Nenhuma modalidade ainda
                </option>
              )}
              {modalities.map((modality) => (
                <option key={modality.id} value={modality.id} className="bg-surface">
                  {modality.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-2">
            <Input
              label="Ou criar uma nova"
              placeholder="Ex. Jiu-jitsu"
              value={newModalityName}
              onChange={(event) => setNewModalityName(event.target.value)}
              className="flex-1"
            />
            <Button
              type="button"
              variant="secondary"
              onClick={handleCreateModality}
              loading={creatingModality}
              className="h-12"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </fieldset>

        <fieldset className="liquid-glass flex flex-col gap-5 rounded-2xl p-6">
          <legend className="px-1 font-display text-sm font-semibold text-white">Dados da turma</legend>
          <Input label="Nome da turma" value={name} onChange={(e) => setName(e.target.value)} />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Capacidade"
              type="number"
              min={1}
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
            />
            <Input label="Local" value={location} onChange={(e) => setLocation(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Idade mínima (opcional)"
              type="number"
              value={minimumAge}
              onChange={(e) => setMinimumAge(e.target.value)}
            />
            <Input
              label="Idade máxima (opcional)"
              type="number"
              value={maximumAge}
              onChange={(e) => setMaximumAge(e.target.value)}
            />
          </div>
        </fieldset>

        <fieldset className="liquid-glass flex flex-col gap-4 rounded-2xl p-6">
          <legend className="px-1 font-display text-sm font-semibold text-white">Horário</legend>
          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-2">
              <label htmlFor="weekday" className="text-sm font-medium text-white">
                Dia
              </label>
              <select
                id="weekday"
                value={weekday}
                onChange={(event) => setWeekday(event.target.value as Weekday)}
                className="h-12 rounded-xl border border-white/10 bg-white/5 px-3 text-white outline-none transition focus:border-brand-green"
              >
                {WEEKDAYS.map((value) => (
                  <option key={value} value={value} className="bg-surface">
                    {WEEKDAY_LABELS[value]}
                  </option>
                ))}
              </select>
            </div>
            <Input
              label="Início"
              type="time"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
            />
            <Input label="Fim" type="time" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} />
          </div>
        </fieldset>

        <fieldset className="liquid-glass flex flex-col gap-3 rounded-2xl p-6">
          <legend className="px-1 font-display text-sm font-semibold text-white">Instrutores</legend>
          {instructors.length === 0 && (
            <p className="text-sm text-white/50">Nenhum instrutor ativo cadastrado na equipe ainda.</p>
          )}
          <div className="flex flex-col gap-2">
            {instructors.map((instructor) => (
              <label key={instructor.id} className="flex items-center gap-2.5 text-sm text-white">
                <input
                  type="checkbox"
                  checked={selectedInstructors.includes(instructor.id)}
                  onChange={() => toggleInstructor(instructor.id)}
                  className="h-4 w-4 rounded border-white/20 bg-white/5 accent-brand-green"
                />
                {instructor.full_name}
              </label>
            ))}
          </div>
        </fieldset>

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        <Button type="submit" loading={submitting} className="w-full sm:w-auto">
          {submitting ? 'Criando…' : 'Criar turma'}
        </Button>
      </form>
    </PageFrame>
  )
}
