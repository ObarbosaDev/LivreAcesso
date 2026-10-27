import { Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/app/routes/ProtectedRoute'
import { AppLayout } from '@/widgets/AppLayout'
import { ComingSoonPage } from '@/pages/ComingSoonPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { LoginPage } from '@/pages/LoginPage'
import { NewStudentPage } from '@/pages/NewStudentPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { StudentsPage } from '@/pages/StudentsPage'
import { UnauthorizedPage } from '@/pages/UnauthorizedPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/entrar" element={<LoginPage />} />
      <Route path="/esqueci-senha" element={<ForgotPasswordPage />} />
      <Route path="/redefinir-senha" element={<ResetPasswordPage />} />
      <Route path="/sem-acesso" element={<UnauthorizedPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/estudantes" element={<StudentsPage />} />
          <Route path="/estudantes/novo" element={<NewStudentPage />} />
          <Route path="/turmas" element={<ComingSoonPage title="Turmas" />} />
          <Route path="/matriculas" element={<ComingSoonPage title="Matrículas" />} />
        </Route>
      </Route>
    </Routes>
  )
}
