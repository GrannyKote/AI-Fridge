import { useEffect, useState } from 'react'
import { adminUsersApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { TextField } from './TextField.jsx'
import { ArrowLeftIcon } from './icons.jsx'
import '../styles/dialog.css'

export function AdminUserPasswordDialog({ user, onClose, onSaved }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
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

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const nextPassword = password.trim()
    if (nextPassword.length < 6) {
      setError('Пароль не короче 6 символов')
      return
    }

    setPending(true)
    try {
      await adminUsersApi.setPassword(user.id, nextPassword)
      onSaved?.()
      onClose()
    } catch (saveError) {
      setFormError(saveError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Смена пароля">
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
          <h2 className="dialog__title">Смена пароля</h2>
        </div>

        <form className="form" onSubmit={handleSubmit} noValidate>
          <p className="admin-users__dialog-login">
            Пользователь: <strong>{user.login}</strong>
          </p>

          <TextField
            label="Новый пароль"
            type="password"
            value={password}
            onChange={(value) => {
              setPassword(value)
              setError('')
            }}
            error={error}
            maxLength={256}
            autoComplete="new-password"
          />

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Сохраняем...' : 'Изменить пароль'}
          </button>
        </form>
      </div>
    </div>
  )
}
