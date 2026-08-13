import { useEffect, useId, useState } from 'react'

export function SuggestInput({
  label,
  value,
  onChange,
  onPick,
  suggestions = [],
  error,
  hint,
  ...inputProps
}) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)

  useEffect(() => {
    setHighlight(0)
  }, [suggestions])

  const visible = open && suggestions.length > 0

  function pick(suggestion) {
    onPick(suggestion)
    setOpen(false)
  }

  function handleKeyDown(event) {
    if (!visible) {
      return
    }

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const shift = event.key === 'ArrowDown' ? 1 : suggestions.length - 1
      setHighlight((current) => (current + shift) % suggestions.length)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      pick(suggestions[highlight])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className={`field${error ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>

      <div className="field__control suggest">
        <input
          {...inputProps}
          id={id}
          className="field__input"
          value={value}
          onChange={(event) => {
            onChange(event.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
          role="combobox"
          aria-expanded={visible}
          aria-autocomplete="list"
        />

        {visible && (
          // preventDefault не даёт полю потерять фокус раньше клика по подсказке
          <ul className="suggest__list" onMouseDown={(event) => event.preventDefault()}>
            {suggestions.map((suggestion, index) => (
              <li key={suggestion.key}>
                <button
                  className={`suggest__option${index === highlight ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => pick(suggestion)}
                  onMouseEnter={() => setHighlight(index)}
                >
                  <span className="suggest__name">{suggestion.label}</span>
                  {suggestion.meta && <span className="suggest__meta">{suggestion.meta}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {error ? (
        <p className="field__error">{error}</p>
      ) : (
        hint && <p className="field__hint">{hint}</p>
      )}
    </div>
  )
}
