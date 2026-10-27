import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/app/routes/ProtectedRoute'
import { AppLayout } from '@/widgets/AppLayout'
import { FullScreenState } from '@/shared/ui/FullScreenState'

const ClassesPage = lazy(() => import('@/pages/ClassesPage').then((module) => ({ default: module.ClassesPage })))
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage })))
const EnrollmentsPage = lazy(() => import('@/pages/EnrollmentsPage').then((module) => ({ default: module.EnrollmentsPage })))
const ForgotPasswordPage = lazy(() => import('@/pages/ForgotPasswordPage').then((module) => ({ default: module.ForgotPasswordPage })))
const LoginPage = lazy(() => import('@/pages/LoginPage').then((module) => ({ default: module.LoginPage })))
const NewClassPage = lazy(() => import('@/pages/NewClassPage').then((module) => ({ default: module.NewClassPage })))
const NewStudentPage = lazy(() => import('@/pages/NewStudentPage').then((module) => ({ default: module.NewStudentPage })))
const ProfilePage = lazy(() => import('@/pages/ProfilePage').then((module) => ({ default: module.ProfilePage })))
const ProfilesAdminPage = lazy(() => import('@/pages/ProfilesAdminPage').then((module) => ({ default: module.ProfilesAdminPage })))
const ResetPasswordPage = lazy(() => import('@/pages/ResetPasswordPage').then((module) => ({ default: module.ResetPasswordPage })))
const ReportsPage = lazy(() => import('@/pages/ReportsPage').then((module) => ({ default: module.ReportsPage })))
const StudentDetailPage = lazy(() => import('@/pages/StudentDetailPage').then((module) => ({ default: module.StudentDetailPage })))
const StudentsPage = lazy(() => import('@/pages/StudentsPage').then((module) => ({ default: module.StudentsPage })))
const UnauthorizedPage = lazy(() => import('@/pages/UnauthorizedPage').then((module) => ({ default: module.UnauthorizedPage })))

export function AppRoutes() {
  return (
    <Suspense fallback={<FullScreenState title="Abrindo o sistema" description="Preparando esta área do Instituto Livre Acesso." loading />}>
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
          <Route path="/estudantes/:studentId" element={<StudentDetailPage />} />
          <Route path="/turmas" element={<ClassesPage />} />
          <Route path="/turmas/nova" element={<NewClassPage />} />
          <Route path="/matriculas" element={<EnrollmentsPage />} />
          <Route path="/relatorios" element={<ReportsPage />} />
          <Route path="/perfil" element={<ProfilePage />} />
          <Route path="/equipe" element={<ProfilesAdminPage />} />
        </Route>
      </Route>
      </Routes>
    </Suspense>
  )
}
