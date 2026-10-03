import { useEffect, useId, useRef, useState } from 'react'
import { feedbackApi } from '../api/client.js'
import { CameraIcon, TrashIcon } from './icons.jsx'
import { FormAlert } from './FormAlert.jsx'
import '../styles/dialog.css'

const MAX_IMAGES = 3
const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const ALLOWED_TYPES = new Set([
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/heic',
  'image/heif',
])

function isAllowedImage(file) {
  return ALLOWED_TYPES.has(file.type)
}

export function FeedbackDialog({ onClose, onSent }) {
  const textId = useId()
  const fileId = useId()
  const fileRef = useRef(null)
  const [text, setText] = useState('')
  const [files, setFiles] = useState([])
  const [previews, setPreviews] = useState([])
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

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
    const urls = files.map((file) => URL.createObjectURL(file))
    setPreviews(urls)
    return () => urls.forEach((url) => URL.revokeObjectURL(url))
  }, [files])

  function addFiles(selected) {
    const nextError = []
    const accepted = []

    for (const file of selected) {
      if (!isAllowedImage(file) || file.type === 'image/svg+xml') {
        nextError.push('Можно прикладывать только изображения')
        continue
      }
      if (file.size > MAX_IMAGE_BYTES) {
        nextError.push('Каждая картинка должна быть не больше 5 МБ')
        continue
      }
      accepted.push(file)
    }

    setFiles((current) => [...current, ...accepted].slice(0, MAX_IMAGES))
    setError(nextError[0] ?? '')
  }

  function removeFile(index) {
    setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index))
    setError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const message = text.trim()
    if (!message) {
      setError('Введите текст отзыва')
      return
    }

    setPending(true)
    try {
      await feedbackApi.create(message, files)
      onSent()
    } catch (submitError) {
      setFormError(submitError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="feedback-title">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <h2 className="dialog__title" id="feedback-title">
          Обратная связь
        </h2>

        <form className="form" onSubmit={handleSubmit} noValidate>
          <div className={`field${error && !text.trim() ? ' field--invalid' : ''}`}>
            <label className="field__label" htmlFor={textId}>
              Отзыв
            </label>
            <div className="field__control">
              <textarea
                id={textId}
                className="field__input field__textarea"
                value={text}
                onChange={(event) => {
                  setText(event.target.value)
                  setError('')
                }}
                placeholder="Расскажите, что можно улучшить"
                rows={5}
                maxLength={4000}
              />
            </div>
            {error && !text.trim() && <p className="field__error">{error}</p>}
          </div>

          <div className="field">
            <span className="field__label" id={`${fileId}-label`}>
              Картинки
            </span>
            <div className="feedback__photos" role="group" aria-labelledby={`${fileId}-label`}>
              {files.map((file, index) => (
                <div className="feedback__photo" key={`${file.name}-${file.size}-${index}`}>
                  <img src={previews[index]} alt="" />
                  <button
                    className="feedback__remove"
                    type="button"
                    onClick={() => removeFile(index)}
                    aria-label={`Удалить ${file.name}`}
                  >
                    <TrashIcon />
                  </button>
                </div>
              ))}

              {files.length < MAX_IMAGES && (
                <button
                  className="feedback__add"
                  type="button"
                  onClick={() => fileRef.current?.click()}
                >
                  <CameraIcon />
                  Добавить
                </button>
              )}
            </div>
            <input
              id={fileId}
              ref={fileRef}
              className="feedback__file"
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => {
                addFiles(Array.from(event.target.files ?? []))
                event.target.value = ''
              }}
            />
            {error && text.trim() ? (
              <p className="field__error">{error}</p>
            ) : (
              <p className="field__hint">До трёх изображений, каждое не больше 5 МБ</p>
            )}
          </div>

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Отправляем...' : 'Отправить'}
          </button>
        </form>
      </div>
    </div>
  )
}
