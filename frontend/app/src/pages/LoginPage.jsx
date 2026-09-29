import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthLayout } from '../components/AuthLayout.jsx'
import { FormAlert } from '../components/FormAlert.jsx'
import { InstallButton } from '../components/InstallButton.jsx'
import { TextField } from '../components/TextField.jsx'
import { useAuth } from '../auth/useAuth.js'
import { hasErrors, validateRequired } from '../lib/validation.js'

export default function LoginPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()

  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({ login: '', password: '' })
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    // При входе проверяем только заполненность: правила формата действуют
    // при регистрации, а в базе могут быть логины, заведённые вручную.
    const nextErrors = {
      login: validateRequired(login, 'Введите логин'),
      password: validateRequired(password, 'Введите пароль'),
    }
    setErrors(nextErrors)

    if (hasErrors(nextErrors)) {
      return
    }

    setPending(true)
    try {
      const account = await signIn(login, password)
      navigate(account.role === 'admin' ? '/admin' : '/', { replace: true })
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <AuthLayout title="Вход" subtitle="Войдите, чтобы открыть свою кладовую">
      <form className="form" onSubmit={handleSubmit} noValidate>
        <TextField
          label="Логин"
          value={login}
          onChange={(value) => {
            setLogin(value)
            setErrors((current) => ({ ...current, login: '' }))
          }}
          error={errors.login}
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
            setErrors((current) => ({ ...current, password: '' }))
          }}
          error={errors.password}
          placeholder="Введите пароль"
          autoComplete="current-password"
          enterKeyHint="go"
        />

        <FormAlert>{formError}</FormAlert>

        <button className="btn btn--primary auth__submit" type="submit" disabled={pending}>
          {pending ? 'Входим...' : 'Войти'}
        </button>
      </form>

      <div className="auth__divider">нет аккаунта?</div>

      <button
        className="btn btn--ghost"
        type="button"
        onClick={() => navigate('/register')}
      >
        Зарегистрироваться
      </button>

      <InstallButton />
    </AuthLayout>
  )
}
