import { useEffect, useId, useState } from 'react'
import { adminNewsApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { TextField } from './TextField.jsx'
import { ArrowLeftIcon } from './icons.jsx'
import '../styles/dialog.css'

export function AdminNewsDialog({ newsId, onClose, onSaved }) {
  const isCreate = newsId == null
  const bodyId = useId()
  const [header, setHeader] = useState('')
  const [body, setBody] = useState('')
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [loading, setLoading] = useState(!isCreate)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape' && !pending) {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose, pending])

  useEffect(() => {
    if (isCreate) {
      return undefined
    }

    let cancelled = false

    async function load() {
      setLoading(true)
      setFormError('')
      try {
        const news = await adminNewsApi.get(newsId)
        if (!cancelled) {
          setHeader(news.header)
          setBody(news.body ?? '')
        }
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
    }
  }, [isCreate, newsId])

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const nextHeader = header.trim()
    if (!nextHeader) {
      setError('Введите заголовок')
      return
    }

    setPending(true)
    try {
      const payload = { header: nextHeader, body: body.trim() }
      const saved = isCreate
        ? await adminNewsApi.create(payload)
        : await adminNewsApi.update(newsId, payload)
      setHeader(saved.header)
      setBody(saved.body ?? '')
      onSaved?.(saved, isCreate)
      if (isCreate) {
        onClose()
      }
    } catch (saveError) {
      setFormError(saveError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Новость">
      <button
        className="dialog__backdrop"
        type="button"
        onClick={pending ? undefined : onClose}
        aria-label="Закрыть"
      />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <div className="news__head">
          <button
            className="icon-btn"
            type="button"
            onClick={onClose}
            disabled={pending}
            aria-label="Назад к списку"
          >
            <ArrowLeftIcon />
          </button>
          <h2 className="dialog__title">{isCreate ? 'Новая новость' : 'Новость'}</h2>
        </div>

        {loading ? (
          <p className="notifications__empty">Загружаем...</p>
        ) : (
          <form className="form" onSubmit={handleSubmit} noValidate>
            <TextField
              label="Заголовок"
              value={header}
              onChange={(value) => {
                setHeader(value)
                setError('')
              }}
              error={error}
              maxLength={1024}
            />

            <div className="field">
              <label className="field__label" htmlFor={bodyId}>
                Текст
              </label>
              <div className="field__control">
                <textarea
                  id={bodyId}
                  className="field__input field__textarea"
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  rows={8}
                  maxLength={20000}
                />
              </div>
            </div>

            <FormAlert>{formError}</FormAlert>

            <button className="btn btn--primary" type="submit" disabled={pending}>
              {pending ? 'Сохраняем...' : 'Сохранить'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
