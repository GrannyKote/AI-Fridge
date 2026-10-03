import { useAuth } from '../auth/useAuth.js'
import { LogoutIcon } from './icons.jsx'

export function AdminHeader() {
  const { user, signOut } = useAuth()

  return (
    <header className="app-header">
      <div className="topbar">
        <h1 className="topbar__name">{user.login}</h1>

        <div className="topbar__actions">
          <button
            className="icon-btn icon-btn--round"
            type="button"
            onClick={signOut}
            aria-label="Выйти из аккаунта"
          >
            <LogoutIcon />
          </button>
        </div>
      </div>
    </header>
  )
}
