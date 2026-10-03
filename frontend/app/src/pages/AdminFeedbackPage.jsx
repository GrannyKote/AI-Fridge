import { useCallback, useEffect, useState } from 'react'
import { adminFeedbackApi } from '../api/client.js'
import { AdminFeedbackDialog } from '../components/AdminFeedbackDialog.jsx'
import { AdminShell } from '../components/AdminShell.jsx'
import '../styles/dialog.css'

const createdAtFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function formatCreatedAt(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : createdAtFormatter.format(date)
}

export default function AdminFeedbackPage() {
  const [items, setItems] = useState([])
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [openId, setOpenId] = useState(null)

  const load = useCallback(async () => {
    setState('loading')
    try {
      setItems(await adminFeedbackApi.list())
      setError('')
      setState('ready')
    } catch (loadError) {
      setError(loadError.message)
      setState('error')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleOpened = useCallback((detail) => {
    setItems((current) =>
      current.map((item) =>
        item.id === detail.id ? { ...item, is_seen: detail.is_seen } : item,
      ),
    )
  }, [])

  return (
    <AdminShell title="Обратная связь">
      {state === 'loading' && <p className="pantry__message">Загружаем отзывы...</p>}

      {state === 'error' && (
        <div className="pantry__message">
          <p>{error}</p>
          <button className="btn btn--ghost" type="button" onClick={load}>
            Повторить
          </button>
        </div>
      )}

      {state === 'ready' && items.length === 0 && (
        <p className="pantry__message">Пока нет отзывов</p>
      )}

      {state === 'ready' && items.length > 0 && (
        <ul className="news__list admin-feedback__list">
          {items.map((item) => (
            <li key={item.id}>
              <button
                className={`admin-feedback__item${item.is_seen ? '' : ' admin-feedback__item--unread'}`}
                type="button"
                onClick={() => setOpenId(item.id)}
              >
                <div className="admin-feedback__head">
                  <span className="news__dot" aria-hidden="true" />
                  <span className="admin-feedback__login">{item.login}</span>
                  <time className="admin-feedback__time" dateTime={item.datetime_created}>
                    {formatCreatedAt(item.datetime_created)}
                  </time>
                </div>
                <p className="admin-feedback__preview">{item.text_preview}</p>
              </button>
            </li>
          ))}
        </ul>
      )}

      {openId != null && (
        <AdminFeedbackDialog
          feedbackId={openId}
          onClose={() => setOpenId(null)}
          onOpened={handleOpened}
        />
      )}
    </AdminShell>
  )
}
