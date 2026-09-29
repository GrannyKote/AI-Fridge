import { useEffect, useState } from 'react'
import { formatRuDate, maskRuDate, parseRuDate } from '../lib/pantry.js'

export function DateField({ id, value, onChange, ariaLabel, className, disabled = false }) {
  const [text, setText] = useState(() => formatRuDate(value))
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    if (!editing) {
      setText(formatRuDate(value))
    }
  }, [value, editing])

  return (
    <input
      id={id}
      className={className}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      placeholder="ДД.ММ.ГГГГ"
      aria-label={ariaLabel}
      disabled={disabled}
      value={text}
      onFocus={() => setEditing(true)}
      onBlur={() => {
        setEditing(false)
        setText(formatRuDate(value))
      }}
      onChange={(event) => {
        const next = maskRuDate(event.target.value)
        setText(next)
        if (next === '') {
          onChange('')
          return
        }
        const iso = parseRuDate(next)
        if (iso) {
          onChange(iso)
        }
      }}
    />
  )
}
