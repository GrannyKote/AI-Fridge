import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider.jsx'
import { useAuth } from './auth/useAuth.js'
import { ThemeProvider } from './theme/ThemeProvider.jsx'
import AdminFeedbackPage from './pages/AdminFeedbackPage.jsx'
import AdminNewsPage from './pages/AdminNewsPage.jsx'
import AdminUsersPage from './pages/AdminUsersPage.jsx'
import ForecastPage from './pages/ForecastPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import PantryPage from './pages/PantryPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import ShoppingPage from './pages/ShoppingPage.jsx'

function homePath(isAdmin) {
  return isAdmin ? '/admin/news' : '/'
}

function RequireUser({ children }) {
  const { isAuthenticated, isAdmin } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (isAdmin) {
    return <Navigate to="/admin/news" replace />
  }

  return children
}

function RequireAdmin({ children }) {
  const { isAuthenticated, isAdmin } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />
  }

  return children
}

function RequireGuest({ children }) {
  const { isAuthenticated, isAdmin } = useAuth()
  return isAuthenticated ? <Navigate to={homePath(isAdmin)} replace /> : children
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route
              path="/"
              element={
                <RequireUser>
                  <PantryPage />
                </RequireUser>
              }
            />
            <Route
              path="/forecast"
              element={
                <RequireUser>
                  <ForecastPage />
                </RequireUser>
              }
            />
            <Route
              path="/shopping"
              element={
                <RequireUser>
                  <ShoppingPage />
                </RequireUser>
              }
            />
            <Route
              path="/settings"
              element={
                <RequireUser>
                  <SettingsPage />
                </RequireUser>
              }
            />
            <Route
              path="/admin/news"
              element={
                <RequireAdmin>
                  <AdminNewsPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/admin/feedback"
              element={
                <RequireAdmin>
                  <AdminFeedbackPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/admin/users"
              element={
                <RequireAdmin>
                  <AdminUsersPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/login"
              element={
                <RequireGuest>
                  <LoginPage />
                </RequireGuest>
              }
            />
            <Route
              path="/register"
              element={
                <RequireGuest>
                  <RegisterPage />
                </RequireGuest>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
