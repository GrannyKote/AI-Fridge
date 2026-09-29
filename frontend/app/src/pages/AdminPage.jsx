import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { feedbackApi } from '../api/client.js'
import { formatRuDate } from '../lib/pantry.js'
import { useAuth } from '../auth/useAuth.js'
import { LogoutIcon } from '../components/icons.jsx'
import '../styles/pantry.css'
import '../styles/settings.css'
import '../styles/feedback.css'

function when(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const day = formatRuDate(
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`,
  )
  return `${day}, ${hours}:${minutes}`
}

export default function AdminPage() {
  const { user, signOut } = useAuth()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (user.role !== 'admin') {
      return undefined
    }

    let cancelled = false
    feedbackApi
      .list(user.id)
      .then((rows) => {
        if (!cancelled) {
          setItems(rows)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
        }
      })

    return () => {
      cancelled = true
    }
  }, [user.id, user.role])

  if (user.role !== 'admin') {
    return <Navigate to="/" replace />
  }

  return (
    <div className="pantry pantry--settings">
      <div className="pantry__app">
        <main className="content">
          <h1 className="settings__title">Админская панель</h1>
          <section className="settings-profile" aria-label="Профиль">
            <div className="settings-profile__text">
              <p className="settings-profile__name">{user.login}</p>
              <p className="settings-profile__meta">Администратор</p>
            </div>
          </section>
          <section className="settings-block" aria-labelledby="admin-feedback-title">
            <h2 className="settings-block__title" id="admin-feedback-title">
              Обратная связь
            </h2>
            {error && <p className="settings-profile__meta">{error}</p>}
            {!error && items.length === 0 && (
              <p className="settings-profile__meta">Сообщений пока нет.</p>
            )}
            {items.map((item) => (
              <article className="admin-mail" key={item.id}>
                <p className="admin-mail__who">{item.login}</p>
                <p className="admin-mail__when">{when(item.date_time)}</p>
                <p className="admin-mail__text">{item.message}</p>
                {item.photos.length > 0 && (
                  <div className="admin-mail__photos">
                    {item.photos.map((photo) => (
                      <img
                        key={photo.id}
                        src={feedbackApi.photoUrl(item.id, photo.id)}
                        alt=""
                      />
                    ))}
                  </div>
                )}
              </article>
            ))}
          </section>
          <section className="settings-block" aria-labelledby="admin-stats-title">
            <h2 className="settings-block__title" id="admin-stats-title">
              Статистика
            </h2>
            <p className="settings-profile__meta">Цифры появятся, когда их назовут.</p>
          </section>
          <button className="settings-logout" type="button" onClick={signOut}>
            <LogoutIcon />
            Выйти из аккаунта
          </button>
        </main>
      </div>
    </div>
  )
}
