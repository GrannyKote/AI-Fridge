import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { newsApi } from './api/client.js'
import { AuthProvider } from './auth/AuthProvider.jsx'
import { useAuth } from './auth/useAuth.js'
import { ThemeProvider } from './theme/ThemeProvider.jsx'
import AdminPage from './pages/AdminPage.jsx'
import FeedbackPage from './pages/FeedbackPage.jsx'
import ForecastPage from './pages/ForecastPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NewsPage from './pages/NewsPage.jsx'
import PantryPage from './pages/PantryPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import ShoppingPage from './pages/ShoppingPage.jsx'

function homeFor(user) {
  return user?.role === 'admin' ? '/admin' : '/'
}

function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function RequireGuest({ children }) {
  const { isAuthenticated, user } = useAuth()
  return isAuthenticated ? <Navigate to={homeFor(user)} replace /> : children
}

function StartPage() {
  const { user } = useAuth()
  if (user?.role === 'admin') {
    return <Navigate to="/admin" replace />
  }
  return <PantryPage />
}

function NewsRedirect() {
  const { isAuthenticated, user } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isAuthenticated || !user || user.role === 'admin' || pathname === '/news') {
      return undefined
    }

    let cancelled = false
    newsApi
      .unread(user.id)
      .then((item) => {
        if (!cancelled && item) {
          navigate('/news', { replace: true })
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [isAuthenticated, navigate, pathname, user])

  return null
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <NewsRedirect />
          <Routes>
            <Route
              path="/"
              element={
                <RequireAuth>
                  <StartPage />
                </RequireAuth>
              }
            />
            <Route
              path="/forecast"
              element={
                <RequireAuth>
                  <ForecastPage />
                </RequireAuth>
              }
            />
            <Route
              path="/shopping"
              element={
                <RequireAuth>
                  <ShoppingPage />
                </RequireAuth>
              }
            />
            <Route
              path="/feedback"
              element={
                <RequireAuth>
                  <FeedbackPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin"
              element={
                <RequireAuth>
                  <AdminPage />
                </RequireAuth>
              }
            />
            <Route
              path="/news"
              element={
                <RequireAuth>
                  <NewsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/settings"
              element={
                <RequireAuth>
                  <SettingsPage />
                </RequireAuth>
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
