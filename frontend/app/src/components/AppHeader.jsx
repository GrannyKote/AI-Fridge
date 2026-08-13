import { useAuth } from '../auth/useAuth.js'
import { BellIcon, MenuIcon } from './icons.jsx'

export function AppHeader({ menuOpen, onToggleMenu, alerts = 0, onBell }) {
  const { user } = useAuth()

  return (
    <header className="topbar">
      <h1 className="topbar__name">{user.login}</h1>

      <div className="topbar__actions">
        <button
          className="icon-btn icon-btn--round"
          type="button"
          onClick={onToggleMenu}
          aria-label={menuOpen ? 'Скрыть меню' : 'Показать меню'}
          aria-expanded={menuOpen}
        >
          <MenuIcon />
        </button>

        <button
          className="icon-btn icon-btn--round"
          type="button"
          onClick={onBell}
          aria-label={alerts > 0 ? `Уведомления, ${alerts}` : 'Уведомления'}
        >
          <BellIcon />
          {alerts > 0 && <span className="icon-btn__badge">{alerts}</span>}
        </button>
      </div>
    </header>
  )
}
