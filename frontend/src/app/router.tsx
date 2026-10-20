import { Navigate, createBrowserRouter } from 'react-router'

import { AppLayout } from '@/app/layouts/AppLayout'
import { NotFoundPage } from '@/app/NotFoundPage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { RequireAuth } from '@/features/auth/RequireAuth'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { ModalitiesPage } from '@/features/modalities/pages/ModalitiesPage'
import { SettingsPage } from '@/features/settings/pages/SettingsPage'
import { StudentDetailPage } from '@/features/students/pages/StudentDetailPage'
import { StudentsEmptyDetail } from '@/features/students/pages/StudentsEmptyDetail'
import { StudentsPage } from '@/features/students/pages/StudentsPage'

// Mapa de URLs → telas. Rotas aninhadas ("children") desenham dentro do
// <Outlet /> do componente pai: AppLayout desenha a sidebar e, no meio,
// a página da rota filha.
export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/app" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    path: '/app',
    // RequireAuth manda para /login quem não tem sessão
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      {
        path: 'alunos',
        element: <StudentsPage />,
        children: [
          { index: true, element: <StudentsEmptyDetail /> },
          { path: ':studentId', element: <StudentDetailPage /> },
        ],
      },
      { path: 'modalidades', element: <ModalitiesPage /> },
      { path: 'configuracoes', element: <SettingsPage /> },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
