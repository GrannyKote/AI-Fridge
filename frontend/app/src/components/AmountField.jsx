import { formatNumber } from '../lib/pantry.js'

export function AmountField({ id, value, onChange, unit, available, error, autoFocus }) {
  const availableText = `${formatNumber(available)}${unit ? ` ${unit}` : ''}`

  return (
    <div className={`field${error ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={id}>
        Количество
      </label>

      <div className="consume__row">
        <div className="field__control">
          <input
            id={id}
            className="field__input field__input--with-suffix"
            type="text"
            inputMode="decimal"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="0"
            autoFocus={autoFocus}
          />
          {unit && <span className="field__suffix">{unit}</span>}
        </div>

        <button
          className="btn btn--ghost btn--compact"
          type="button"
          onClick={() => onChange(formatNumber(available))}
        >
          Полностью
        </button>
      </div>

      {error ? (
        <p className="field__error">{error}</p>
      ) : (
        <p className="field__hint">Доступно {availableText}</p>
      )}
    </div>
  )
}
