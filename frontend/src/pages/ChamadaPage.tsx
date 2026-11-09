import { useEffect, useState } from 'react'

import { useAuth } from '@/app/providers/AuthProvider'
import { listClasses } from '@/features/classes/api'
import type { SchoolClass } from '@/entities/class/types'
import { AttendanceSection } from '@/pages/AttendanceSection'
import { usePageTitle } from '@/shared/lib/usePageTitle'
import { PageFrame } from '@/shared/ui/PageFrame'
import { Select } from '@/shared/ui/Select'

/** Chamada é escopada por turma, igual Matrículas: a tela parte da turma
 * selecionada e delega o resto para a mesma seção usada em Turmas. */
export function ChamadaPage() {
  usePageTitle('Chamada')
  const { profile } = useAuth()
  const canTakeAttendance = profile?.capabilities.includes('attendance:manage') ?? false

  const [classes, setClasses] = useState<SchoolClass[] | null>(null)
  const [selectedClassId, setSelectedClassId] = useState('')

  useEffect(() => {
    listClasses({ active: true, page: 1, pageSize: 100 })
      .then((result) => setClasses(result.items))
      .catch(() => setClasses([]))
  }, [])

  return (
    <PageFrame
      eyebrow="Frequência"
      title="Chamada"
      description="Marque presença por turma, consulte o histórico dos últimos 6 meses e o resumo mensal."
    >
      <div className="liquid-glass border-t-2 border-t-brand-green/50 p-4 sm:p-5">
        <Select
          label="Turma"
          value={selectedClassId}
          onChange={(event) => setSelectedClassId(event.target.value)}
          options={[
            { value: '', label: classes ? 'Selecione uma turma' : 'Carregando turmas…' },
            ...(classes ?? []).map((item) => ({ value: item.id, label: item.name })),
          ]}
        />
      </div>

      {selectedClassId && (
        <div className="mt-6">
          <AttendanceSection classId={selectedClassId} canTakeAttendance={canTakeAttendance} showHeader={false} />
        </div>
      )}
    </PageFrame>
  )
}
