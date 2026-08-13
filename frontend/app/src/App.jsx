import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthProvider.jsx'
import { useAuth } from './auth/useAuth.js'
import ForecastPage from './pages/ForecastPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import PantryPage from './pages/PantryPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import ShoppingPage from './pages/ShoppingPage.jsx'

function RequireAuth({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

function RequireGuest({ children }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <Navigate to="/" replace /> : children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              <RequireAuth>
                <PantryPage />
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
  )
}
