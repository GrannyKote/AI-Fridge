import { useState } from 'react'
import { useAuth } from '../auth/useAuth.js'
import { AppHeader } from '../components/AppHeader.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { ClipboardListIcon, LogoutIcon, MoonIcon } from '../components/icons.jsx'
import { useTheme } from '../theme/useTheme.js'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'
import '../styles/settings.css'

export default function SettingsPage() {
  const { user, signOut } = useAuth()
  const { isDark, setDark } = useTheme()
  const [menuOpen, setMenuOpen] = useState(false)
  const [toast, setToast] = useToast()

  const letter = (user.login?.trim()?.[0] ?? '?').toUpperCase()
  const groupName = user.groups?.[0]?.name ?? ''

  return (
    <div className={`pantry pantry--settings${menuOpen ? ' pantry--menu-open' : ''}`}>
      <div className="pantry__app">
        <AppHeader
          menuOpen={menuOpen}
          onToggleMenu={() => setMenuOpen((open) => !open)}
          onBell={() => setToast('Уведомления появятся позже')}
          onToast={setToast}
        />

        <main className="content">
          <h1 className="settings__title">Настройки</h1>

          <section className="settings-profile" aria-label="Профиль">
            <div className="settings-profile__avatar" aria-hidden="true">
              {letter}
            </div>
            <div className="settings-profile__text">
              <p className="settings-profile__name">{user.login}</p>
              {groupName && <p className="settings-profile__meta">{groupName}</p>}
            </div>
          </section>

          <section className="settings-block" aria-labelledby="appearance-title">
            <h2 className="settings-block__title" id="appearance-title">
              Внешний вид
            </h2>

            <div className="settings-row">
              <span className="settings-row__label">
                <MoonIcon />
                Тёмная тема
              </span>
              <button
                className={`theme-switch${isDark ? ' is-on' : ''}`}
                type="button"
                role="switch"
                aria-checked={isDark}
                aria-label="Тёмная тема"
                onClick={() => setDark(!isDark)}
              >
                <span className="theme-switch__thumb" />
              </button>
            </div>
          </section>

          <div className="settings-footer">
            <section className="settings-about" aria-label="О приложении">
              <div className="settings-about__head">
                <span className="settings-about__icon" aria-hidden="true">
                  <ClipboardListIcon />
                </span>
                <h2 className="settings-about__title">AI-Fridge</h2>
                <span className="settings-about__badge">{import.meta.env.VITE_APP_VERSION || 'MVP 0.0.1'}</span>
              </div>
              <p className="settings-about__text">
                Умный помощник для учёта продуктов дома. Прогнозирует потребление,
                предупреждает об истечении сроков, автоматически формирует список покупок.
              </p>
            </section>

            <button className="settings-logout" type="button" onClick={signOut}>
              <LogoutIcon />
              Выйти из аккаунта
            </button>
          </div>
        </main>
      </div>

      <PantryDock
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onSignOut={signOut}
      />

      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
