import { useEffect, useState } from 'react'
import { adminNewsApi } from '../api/client.js'
import { ArrowLeftIcon } from './icons.jsx'
import '../styles/dialog.css'

const seenAtFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function formatSeenAt(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : seenAtFormatter.format(date)
}

export function AdminNewsSeenDialog({ newsId, header, onClose }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const viewers = await adminNewsApi.viewers(newsId)
        if (!cancelled) {
          setItems(viewers)
          setError('')
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [newsId])

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Просмотры новости">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <div className="news__head">
          <button className="icon-btn" type="button" onClick={onClose} aria-label="Назад к списку">
            <ArrowLeftIcon />
          </button>
          <h2 className="dialog__title">Кто прочитал</h2>
        </div>

        {header && <p className="dialog__subtitle">{header}</p>}

        <div className="notifications__panel">
          {loading ? (
            <p className="notifications__empty">Загружаем...</p>
          ) : error ? (
            <p className="notifications__empty">{error}</p>
          ) : items.length === 0 ? (
            <p className="notifications__empty">Пока никто не открывал эту новость</p>
          ) : (
            <ul className="admin-news__viewers">
              {items.map((item) => (
                <li className="admin-news__viewer" key={`${item.login}-${item.datetime_seen}`}>
                  <span className="admin-news__viewer-login">{item.login}</span>
                  <span className="admin-news__viewer-time">{formatSeenAt(item.datetime_seen)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
