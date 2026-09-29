import { useId, useState } from 'react'
import { feedbackApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { AppHeader } from '../components/AppHeader.jsx'
import { PantryDock } from '../components/PantryDock.jsx'
import { useToast } from '../lib/useToast.js'
import '../styles/pantry.css'
import '../styles/settings.css'
import '../styles/feedback.css'

export default function FeedbackPage() {
  const { user, signOut } = useAuth()
  const fieldId = useId()
  const [menuOpen, setMenuOpen] = useState(false)
  const [toast, setToast] = useToast()
  const photoId = useId()
  const [text, setText] = useState('')
  const [photos, setPhotos] = useState([])
  const [pending, setPending] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  function addPhotos(list) {
    const incoming = [...list].filter((file) => file.type.startsWith('image/'))
    const room = 5 - photos.length
    if (room <= 0 || incoming.length > room) {
      setError('Можно приложить не больше пяти фото')
    }
    const accepted = incoming.slice(0, Math.max(room, 0)).map((file) => ({
      file,
      url: URL.createObjectURL(file),
    }))
    if (accepted.length > 0) {
      setPhotos((current) => [...current, ...accepted])
      setSent(false)
    }
  }

  function removePhoto(index) {
    setPhotos((current) => {
      const next = current.filter((item, at) => {
        if (at === index) {
          URL.revokeObjectURL(item.url)
          return false
        }
        return true
      })
      return next
    })
  }

  async function submit(event) {
    event.preventDefault()
    const message = text.trim()
    if (!message) {
      setError('Напишите сообщение')
      setSent(false)
      return
    }

    setPending(true)
    setError('')
    try {
      const result = await feedbackApi.send(
        user.id,
        message,
        photos.map((item) => item.file),
      )
      setText('')
      for (const item of photos) {
        URL.revokeObjectURL(item.url)
      }
      setPhotos([])
      setSent(result.status)
    } catch (err) {
      setSent(false)
      setError(err.message)
    } finally {
      setPending(false)
    }
  }

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
          <h1 className="settings__title">Обратная связь</h1>

          <form className="feedback" onSubmit={submit}>
            <div className={`field${error ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor={fieldId}>
                Сообщение
              </label>
              <textarea
                id={fieldId}
                className="field__input feedback__text"
                value={text}
                maxLength={2000}
                rows={6}
                placeholder="Что поправить или что не сработало"
                onChange={(event) => {
                  setText(event.target.value)
                  setSent(false)
                }}
              />
              {error && <p className="field__error">{error}</p>}
            </div>

            <div className="feedback__photos">
              {photos.map((item, index) => (
                <div className="feedback__photo" key={item.url}>
                  <img src={item.url} alt="" />
                  <button
                    className="feedback__photo-remove"
                    type="button"
                    onClick={() => removePhoto(index)}
                    aria-label="Убрать фото"
                  >
                    Убрать
                  </button>
                </div>
              ))}
            </div>

            {photos.length < 5 && (
              <>
                <input
                  id={photoId}
                  className="feedback__file"
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={(event) => {
                    addPhotos(event.target.files ?? [])
                    event.target.value = ''
                  }}
                />
                <label className="btn feedback__attach" htmlFor={photoId}>
                  Добавить фото
                </label>
              </>
            )}

            <button className="btn btn--primary" type="submit" disabled={pending}>
              {pending ? 'Отправляем...' : 'Отправить'}
            </button>

            {sent && (
              <p className="feedback__sent" role="status">
                {sent}
              </p>
            )}
          </form>
        </main>
      </div>

      <PantryDock open={menuOpen} onClose={() => setMenuOpen(false)} onSignOut={signOut} />

      <div className={`toast${toast ? ' is-visible' : ''}`} role="status" aria-live="polite">
        {toast}
      </div>
    </div>
  )
}
