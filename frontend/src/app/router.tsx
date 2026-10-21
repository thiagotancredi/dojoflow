import { Navigate, createBrowserRouter } from 'react-router'

import { AppLayout } from '@/app/layouts/AppLayout'
import { NotFoundPage } from '@/app/NotFoundPage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { SetAccessPage } from '@/features/auth/pages/SetAccessPage'
import { RequireAuth } from '@/features/auth/RequireAuth'
import { BulkBeltsPage } from '@/features/belts/pages/BulkBeltsPage'
import { ModalityBeltsPage } from '@/features/belts/pages/ModalityBeltsPage'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { GraduationListPage } from '@/features/graduations/pages/GraduationListPage'
import { GraduationListsPage } from '@/features/graduations/pages/GraduationListsPage'
import { SettingsPage } from '@/features/settings/pages/SettingsPage'
import { NewStudentPage } from '@/features/students/pages/NewStudentPage'
import { StudentDetailPage } from '@/features/students/pages/StudentDetailPage'
import { StudentsEmptyDetail } from '@/features/students/pages/StudentsEmptyDetail'
import { StudentsPage } from '@/features/students/pages/StudentsPage'

// Mapa de URLs → telas. Rotas aninhadas ("children") desenham dentro do
// <Outlet /> do componente pai: AppLayout desenha a sidebar e, no meio,
// a página da rota filha.
export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/app" replace /> },
  { path: '/login', element: <LoginPage /> },
  // Link do /web no bot: definir e-mail e senha (público, o token prova quem é)
  { path: '/definir-acesso', element: <SetAccessPage /> },
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
      // Cadastro em tela própria (fora do mestre-detalhe da lista)
      { path: 'alunos/novo', element: <NewStudentPage /> },
      {
        path: 'alunos',
        element: <StudentsPage />,
        children: [
          { index: true, element: <StudentsEmptyDetail /> },
          { path: ':studentId', element: <StudentDetailPage /> },
        ],
      },
      // Modalidades agora ficam dentro de Configurações
      {
        path: 'modalidades',
        element: <Navigate to="/app/configuracoes" replace />,
      },
      { path: 'graduacoes', element: <GraduationListsPage /> },
      { path: 'graduacoes/:listId', element: <GraduationListPage /> },
      { path: 'configuracoes', element: <SettingsPage /> },
      {
        path: 'configuracoes/modalidades/:modalityId/faixas',
        element: <ModalityBeltsPage />,
      },
      {
        path: 'configuracoes/modalidades/:modalityId/faixas/lancar',
        element: <BulkBeltsPage />,
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
