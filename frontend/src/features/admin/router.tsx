import { createBrowserRouter, Navigate } from 'react-router'

import { AdminLayout } from '@/features/admin/AdminLayout'
import { AdminAcademiesPage } from '@/features/admin/pages/AdminAcademiesPage'
import { RequireAdmin } from '@/features/admin/RequireAdmin'
import { LoginPage } from '@/features/auth/pages/LoginPage'

// Rotas do painel do administrador (só no endereço admin.*)
export const adminRouter = createBrowserRouter([
  { path: '/login', element: <LoginPage redirectTo="/" variant="admin" /> },
  {
    path: '/',
    element: (
      <RequireAdmin>
        <AdminLayout />
      </RequireAdmin>
    ),
    children: [{ index: true, element: <AdminAcademiesPage /> }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])
