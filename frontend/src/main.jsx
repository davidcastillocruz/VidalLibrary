import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router';

import RequireRole from '@/components/RequireRole/RequireRole';
import AdminLayout from '@/features/admin/layouts/AdminLayout/AdminLayout';
import AdminCatalogPage from '@/features/admin/pages/AdminCatalogPage/AdminCatalogPage';
import DeskPage from '@/features/admin/pages/DeskPage/DeskPage';
import ItemFormPage from '@/features/admin/pages/ItemFormPage/ItemFormPage';
import ListsPage from '@/features/admin/pages/ListsPage/ListsPage';
import UsersPage from '@/features/admin/pages/UsersPage/UsersPage';
import CurrentUserProvider from '@/features/auth/currentUser/CurrentUserProvider';
import ForgotPasswordPage from '@/features/auth/pages/ForgotPasswordPage/ForgotPasswordPage';
import LoginPage from '@/features/auth/pages/LoginPage/LoginPage';
import NewPasswordPage from '@/features/auth/pages/NewPasswordPage/NewPasswordPage';
import CatalogPage from '@/features/catalog/pages/CatalogPage/CatalogPage';
import ItemPage from '@/features/catalog/pages/ItemPage/ItemPage';
import MyLoansPage from '@/features/loans/pages/MyLoansPage/MyLoansPage';
import LanguageProvider from '@/languages/LanguageProvider';
import AppLayout from '@/layouts/AppLayout/AppLayout';
import NotificationProvider from '@/notifications/NotificationProvider';
import NotFoundPage from '@/pages/NotFoundPage/NotFoundPage';
import ThemeProvider from '@/themes/ThemeProvider';
import { applyTheme, getInitialTheme } from '@/themes/themes';
import '@/themes/themes.css';
import '@/index.css';

// The links of the emails point here: /invitation?token=, /password/reset?token=, /loans and /items/<id>
const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <CatalogPage /> },
      { path: '/items/:id', element: <ItemPage /> },
      { path: '/login', element: <LoginPage /> },
      { path: '/password/forgot', element: <ForgotPasswordPage /> },
      { path: '/password/reset', element: <NewPasswordPage mode="reset" /> },
      { path: '/invitation', element: <NewPasswordPage mode="invitation" /> },
      {
        element: <RequireRole />,
        children: [{ path: '/loans', element: <MyLoansPage /> }],
      },
      {
        element: <RequireRole role="librarian" />,
        children: [
          {
            path: '/admin',
            element: <AdminLayout />,
            children: [
              { index: true, element: <Navigate to="/admin/loans" replace /> },
              { path: 'loans', element: <DeskPage /> },
              { path: 'catalog', element: <AdminCatalogPage /> },
              { path: 'catalog/new', element: <ItemFormPage key="new" /> },
              { path: 'catalog/:id', element: <ItemFormPage /> },
              { path: 'lists', element: <ListsPage /> },
              { path: 'users', element: <UsersPage /> },
            ],
          },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

applyTheme(getInitialTheme());

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <NotificationProvider>
          <CurrentUserProvider>
            <RouterProvider router={router} />
          </CurrentUserProvider>
        </NotificationProvider>
      </LanguageProvider>
    </ThemeProvider>
  </StrictMode>,
);
