import { useState } from 'react'
import { prepareOffline, synchronizeOffline } from '../api/client.js'
import { changeMode } from '../api/offlineStore.js'
import { useOfflineStatus } from '../api/useOfflineStatus.js'
import { useAuth } from '../auth/useAuth.js'
import { AppHeader } from '../components/AppHeader.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { ClipboardListIcon, LogoutIcon, MoonIcon } from '../components/icons.jsx'
import { useTheme } from '../theme/useTheme.js'
import { APP_VERSION } from '../lib/appVersion.js'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'
import '../styles/settings.css'

export default function SettingsPage() {
  const { user, signOut } = useAuth()
  const { isDark, setDark } = useTheme()
  const [toast, setToast] = useToast()
  const [busy, setBusy] = useState(false)
  const { enabled, pending, error } = useOfflineStatus(user)

  async function run(action) {
    setBusy(true)
    try {
      await action()
    } catch (failure) {
      setToast(failure.message)
    } finally {
      setBusy(false)
    }
  }

  function toggleMode() {
    return run(async () => {
      await changeMode(user, !enabled)
      if (!enabled) await prepareOffline(user)
    })
  }

  const letter = (user.login?.trim()?.[0] ?? '?').toUpperCase()
  const groupName = user.groups?.[0]?.name ?? ''

  return (
    <div className="pantry pantry--settings">
      <div className="pantry__app">
        <AppHeader onToast={setToast} />

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

          <section className="settings-block" aria-labelledby="data-mode-title">
            <h2 className="settings-block__title" id="data-mode-title">Режим работы</h2>
            <div className="settings-row">
              <span className="settings-row__label">{enabled ? 'Offline-first' : 'Online-only'}</span>
              <button
                className={`theme-switch${enabled ? ' is-on' : ''}`}
                type="button"
                role="switch"
                aria-label="Offline-first"
                aria-checked={enabled}
                disabled={busy || pending > 0}
                onClick={toggleMode}
              >
                <span className="theme-switch__thumb" />
              </button>
            </div>
            <p className="settings-about__text" role="status">
              {pending > 0
                ? `Изменений в очереди: ${pending}. Для смены режима завершите синхронизацию.`
                : enabled
                  ? 'Кладовая и покупки доступны после первой загрузки. Изменения отправляются при подключении.'
                  : 'Чтение и изменение данных требуют подключения к серверу.'}
            </p>
            {error && <p className="settings-about__text" role="alert">{error}</p>}
            {pending > 0 && (
              <button className="btn btn--ghost" type="button" disabled={busy}
                onClick={() => run(() => synchronizeOffline(user, 'retry'))}>
                Синхронизировать
              </button>
            )}
            {error && pending > 0 && (
              <button className="btn btn--ghost" type="button" disabled={busy}
                onClick={() => {
                  if (window.confirm('Удалить все неподтверждённые изменения с этого устройства?')) {
                    run(() => synchronizeOffline(user, 'discard'))
                  }
                }}>
                Удалить неподтверждённые изменения
              </button>
            )}
          </section>

          <div className="settings-footer">
            <section className="settings-about" aria-label="О приложении">
              <div className="settings-about__head">
                <span className="settings-about__icon" aria-hidden="true">
                  <ClipboardListIcon />
                </span>
                <h2 className="settings-about__title">AI-Fridge</h2>
                <span className="settings-about__badge">{APP_VERSION}</span>
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

      <PantryDock />

      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
