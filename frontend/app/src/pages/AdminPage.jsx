import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { adminApi, feedbackApi, newsApi } from '../api/client.js'
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

const EMPTY_STATS = {
  products: { day: 0, week: 0, month: 0 },
  users: { day: 0, week: 0, month: 0 },
}

const PERIODS = [
  ['day', '24 часа'],
  ['week', '7 дней'],
  ['month', 'Месяц'],
]

export default function AdminPage() {
  const { user, signOut } = useAuth()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [stats, setStats] = useState(EMPTY_STATS)
  const [news, setNews] = useState([])
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [newsError, setNewsError] = useState('')
  const [pending, setPending] = useState(false)

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

    adminApi
      .stats(user.id)
      .then((rows) => {
        if (!cancelled) {
          setStats(rows)
        }
      })
      .catch(() => {})

    newsApi
      .list()
      .then((rows) => {
        if (!cancelled) {
          setNews(rows)
        }
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [user.id, user.role])

  async function deleteNews(newsId) {
    setNewsError('')
    try {
      await newsApi.remove(user.id, newsId)
      setNews((rows) => rows.filter((item) => item.id !== newsId))
    } catch (err) {
      setNewsError(err.message)
    }
  }

  async function sendNews(event) {
    event.preventDefault()
    setNewsError('')
    const nextTitle = title.trim()
    const nextBody = body.trim()
    if (!nextTitle || !nextBody) {
      setNewsError('Укажите заголовок и текст')
      return
    }

    setPending(true)
    try {
      const created = await newsApi.publish(user.id, nextTitle, nextBody)
      setNews((rows) => [created, ...rows])
      setTitle('')
      setBody('')
    } catch (err) {
      setNewsError(err.message)
    } finally {
      setPending(false)
    }
  }

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
            <div className="admin-stats">
              <div>
                <h3>Уникальные продукты</h3>
                <ul>
                  {PERIODS.map(([key, label]) => (
                    <li key={key}>
                      <span>{label}</span>
                      <span>{stats.products[key]}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Пользователи</h3>
                <p className="settings-profile__meta">загрузили хотя бы один продукт</p>
                <ul>
                  {PERIODS.map(([key, label]) => (
                    <li key={key}>
                      <span>{label}</span>
                      <span>{stats.users[key]}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
          <section className="settings-block" aria-labelledby="admin-news-title">
            <h2 className="settings-block__title" id="admin-news-title">
              Новость
            </h2>
            <form className="feedback" onSubmit={sendNews}>
              <div className="field">
                <label className="field__label" htmlFor="news-title">
                  Заголовок
                </label>
                <input
                  id="news-title"
                  className="field__input"
                  value={title}
                  maxLength={200}
                  onChange={(event) => setTitle(event.target.value)}
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="news-body">
                  Текст
                </label>
                <textarea
                  id="news-body"
                  className="field__input feedback__text"
                  value={body}
                  maxLength={4000}
                  onChange={(event) => setBody(event.target.value)}
                />
              </div>
              {newsError && <p className="field__error">{newsError}</p>}
              <button className="btn btn--primary" type="submit" disabled={pending}>
                Отправить
              </button>
            </form>
            {news.map((item) => (
              <article className="admin-mail" key={item.id}>
                <p className="admin-mail__when">{when(item.date_time)}</p>
                <p className="admin-mail__who">{item.title}</p>
                <p className="admin-mail__text">{item.body}</p>
                <button className="admin-mail__delete" type="button" onClick={() => deleteNews(item.id)}>
                  Удалить у всех
                </button>
              </article>
            ))}
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
