import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider.jsx'
import { useAuth } from './auth/useAuth.js'
import { ThemeProvider } from './theme/ThemeProvider.jsx'
import AdminPage from './pages/AdminPage.jsx'
import FeedbackPage from './pages/FeedbackPage.jsx'
import ForecastPage from './pages/ForecastPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
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

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
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
