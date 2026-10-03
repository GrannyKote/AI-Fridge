import { useEffect, useState } from 'react'
import { newsApi } from '../api/client.js'
import { ArrowLeftIcon } from './icons.jsx'
import '../styles/dialog.css'

export function NewsDialog({ onClose, onChanged }) {
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key !== 'Escape') {
        return
      }
      if (selected) {
        setSelected(null)
        return
      }
      onClose()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose, selected])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const news = await newsApi.list()
        if (!cancelled) {
          setItems(news)
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
  }, [])

  async function openNews(item) {
    setSelected({ id: item.id, header: item.header, body: '', is_seen: item.is_seen })

    try {
      const opened = await newsApi.markSeen(item.id)
      setSelected(opened)
      setItems((current) =>
        current.map((news) => (news.id === item.id ? { ...news, is_seen: true } : news)),
      )
      if (!item.is_seen) {
        onChanged?.()
      }
    } catch (openError) {
      setError(openError.message)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Новости">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        {selected ? (
          <>
            <div className="news__head">
              <button
                className="icon-btn"
                type="button"
                onClick={() => setSelected(null)}
                aria-label="Назад к списку"
              >
                <ArrowLeftIcon />
              </button>
              <h2 className="dialog__title">{selected.header}</h2>
            </div>

            <div className="news__body">{selected.body || ''}</div>
          </>
        ) : (
          <>
            <h2 className="dialog__title">Новости</h2>

            <div className="notifications__panel">
              {loading ? (
                <p className="notifications__empty">Загружаем...</p>
              ) : error ? (
                <p className="notifications__empty">{error}</p>
              ) : items.length === 0 ? (
                <p className="notifications__empty">Пока нет новостей</p>
              ) : (
                <ul className="news__list">
                  {items.map((item) => (
                    <li key={item.id}>
                      <button
                        className={`news__item${item.is_seen ? ' news__item--seen' : ''}`}
                        type="button"
                        onClick={() => openNews(item)}
                      >
                        <span className="news__dot" aria-hidden="true" />
                        <span className="news__header">{item.header}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
