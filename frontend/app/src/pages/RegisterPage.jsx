import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../components/AuthLayout.jsx'
import { FormAlert } from '../components/FormAlert.jsx'
import { TextField } from '../components/TextField.jsx'
import { useAuth } from '../auth/useAuth.js'
import {
  PASSWORD_MIN,
  hasErrors,
  validateLogin,
  validatePassword,
  validatePasswordRepeat,
} from '../lib/validation.js'

export default function RegisterPage() {
  const { signUp } = useAuth()
  const navigate = useNavigate()

  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [passwordRepeat, setPasswordRepeat] = useState('')
  const [errors, setErrors] = useState({ login: '', password: '', passwordRepeat: '' })
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  function clearError(field) {
    setErrors((current) => ({ ...current, [field]: '' }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const nextErrors = {
      login: validateLogin(login),
      password: validatePassword(password),
      passwordRepeat: validatePasswordRepeat(password, passwordRepeat),
    }
    setErrors(nextErrors)

    if (hasErrors(nextErrors)) {
      return
    }

    setPending(true)
    try {
      await signUp(login, password)
      navigate('/', { replace: true })
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <AuthLayout
      title="Регистрация"
      subtitle="Создайте аккаунт, чтобы следить за продуктами"
      backTo="/login"
    >
      <form className="form" onSubmit={handleSubmit} noValidate>
        <TextField
          label="Логин"
          value={login}
          onChange={(value) => {
            setLogin(value)
            clearError('login')
          }}
          error={errors.login}
          hint="Латиница, цифры и знаки . _ -"
          placeholder="Например, ivan.petrov"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck="false"
          enterKeyHint="next"
        />

        <TextField
          label="Пароль"
          type="password"
          value={password}
          onChange={(value) => {
            setPassword(value)
            clearError('password')
            clearError('passwordRepeat')
          }}
          error={errors.password}
          hint={`Минимум ${PASSWORD_MIN} символов`}
          placeholder="Придумайте пароль"
          autoComplete="new-password"
          enterKeyHint="next"
        />

        <TextField
          label="Повторить пароль"
          type="password"
          value={passwordRepeat}
          onChange={(value) => {
            setPasswordRepeat(value)
            clearError('passwordRepeat')
          }}
          error={errors.passwordRepeat}
          placeholder="Введите пароль ещё раз"
          autoComplete="new-password"
          enterKeyHint="go"
        />

        <FormAlert>{formError}</FormAlert>

        <button className="btn btn--primary auth__submit" type="submit" disabled={pending}>
          {pending ? 'Создаём аккаунт...' : 'Зарегистрироваться'}
        </button>
      </form>

      <div className="auth__footer">
        <p className="auth__note">
          Уже есть аккаунт?{' '}
          <Link className="btn btn--link" to="/login">
            Войти
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
