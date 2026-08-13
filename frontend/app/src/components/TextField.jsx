import { useId, useState } from 'react'
import { EyeIcon, EyeOffIcon } from './icons.jsx'

export function TextField({
  label,
  type = 'text',
  value,
  onChange,
  error,
  hint,
  ...inputProps
}) {
  const id = useId()
  const [revealed, setRevealed] = useState(false)

  const isPassword = type === 'password'
  const messageId = error || hint ? `${id}-message` : undefined

  return (
    <div className={`field${error ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>

      <div className="field__control">
        <input
          {...inputProps}
          id={id}
          className={`field__input${isPassword ? ' field__input--with-action' : ''}`}
          type={isPassword && revealed ? 'text' : type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={messageId}
        />

        {isPassword && (
          <button
            className="field__toggle"
            type="button"
            onClick={() => setRevealed((current) => !current)}
            aria-label={revealed ? 'Скрыть пароль' : 'Показать пароль'}
          >
            {revealed ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        )}
      </div>

      {error ? (
        <p className="field__error" id={messageId}>
          {error}
        </p>
      ) : (
        hint && (
          <p className="field__hint" id={messageId}>
            {hint}
          </p>
        )
      )}
    </div>
  )
}
