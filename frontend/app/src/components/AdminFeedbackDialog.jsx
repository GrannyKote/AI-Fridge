import { useEffect, useState } from 'react'
import { adminFeedbackApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { ArrowLeftIcon } from './icons.jsx'
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

export function AdminFeedbackDialog({ feedbackId, onClose, onOpened }) {
  const [detail, setDetail] = useState(null)
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(true)
  const [previews, setPreviews] = useState([])
  const [downloadingId, setDownloadingId] = useState(null)

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape' && !downloadingId) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [downloadingId, onClose])

  useEffect(() => {
    let cancelled = false
    let objectUrls = []

    async function load() {
      setLoading(true)
      setFormError('')
      setPreviews([])
      try {
        const nextDetail = await adminFeedbackApi.get(feedbackId)
        if (cancelled) {
          return
        }
        setDetail(nextDetail)
        onOpened?.(nextDetail)

        const nextPreviews = await Promise.all(
          (nextDetail.items ?? []).map(async (item) => {
            const blob = await adminFeedbackApi.fetchItem(feedbackId, item.id)
            const url = URL.createObjectURL(blob)
            return { id: item.id, url }
          }),
        )
        if (cancelled) {
          for (const preview of nextPreviews) {
            URL.revokeObjectURL(preview.url)
          }
          return
        }
        objectUrls = nextPreviews.map((preview) => preview.url)
        setPreviews(nextPreviews)
      } catch (loadError) {
        if (!cancelled) {
          setFormError(loadError.message)
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
      for (const url of objectUrls) {
        URL.revokeObjectURL(url)
      }
    }
  }, [feedbackId, onOpened])

  async function handleDownload(itemId) {
    if (downloadingId) {
      return
    }
    setDownloadingId(itemId)
    try {
      await adminFeedbackApi.downloadItem(feedbackId, itemId)
    } catch (downloadError) {
      setFormError(downloadError.message)
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Отзыв">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <div className="news__head">
          <button className="icon-btn" type="button" onClick={onClose} aria-label="Назад к списку">
            <ArrowLeftIcon />
          </button>
          <h2 className="dialog__title">Отзыв</h2>
        </div>

        {loading && <p className="notifications__empty">Загружаем...</p>}

        {!loading && formError && !detail && (
          <p className="notifications__empty">{formError}</p>
        )}

        {!loading && detail && (
          <div className="admin-feedback__detail">
            <div className="admin-feedback__detail-head">
              <span className="admin-feedback__login">{detail.login}</span>
              <time className="admin-feedback__time" dateTime={detail.datetime_created}>
                {formatCreatedAt(detail.datetime_created)}
              </time>
            </div>

            <p className="admin-feedback__text">{detail.feedback_text}</p>

            {previews.length > 0 && (
              <ul className="admin-feedback__photos">
                {previews.map((preview) => (
                  <li key={preview.id}>
                    <button
                      className="admin-feedback__photo-btn"
                      type="button"
                      onClick={() => handleDownload(preview.id)}
                      disabled={downloadingId === preview.id}
                      aria-label="Скачать изображение в полном размере"
                    >
                      <img
                        className="admin-feedback__photo"
                        src={preview.url}
                        alt=""
                        loading="lazy"
                      />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <FormAlert>{formError}</FormAlert>
          </div>
        )}
      </div>
    </div>
  )
}
