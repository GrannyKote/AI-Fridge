import { useState } from 'react'
import { maskDateInput, toDisplayDate, toIsoDate } from '../lib/pantry.js'
import { CalendarIcon } from './icons.jsx'

export function DateInput({ id, value, onChange, disabled }) {
  const [draft, setDraft] = useState(null)
  const text = draft ?? toDisplayDate(value)

  return (
    <div className="field__date">
      <input
        id={id}
        className="field__input field__input--with-action"
        type="text"
        inputMode="numeric"
        autoComplete="off"
        placeholder="дд/мм/гггг"
        maxLength={10}
        disabled={disabled}
        value={text}
        onChange={(event) => {
          const next = maskDateInput(event.target.value)
          setDraft(next)
          onChange(toIsoDate(next))
        }}
        onFocus={() => setDraft(toDisplayDate(value))}
        onBlur={() => {
          const iso = toIsoDate(text)
          onChange(iso)
          setDraft(null)
        }}
      />
      <span className="field__toggle" aria-hidden="true">
        <CalendarIcon />
      </span>
      <input
        className="field__date-picker"
        type="date"
        tabIndex={-1}
        disabled={disabled}
        value={value}
        onChange={(event) => {
          setDraft(null)
          onChange(event.target.value)
        }}
        aria-label="Открыть календарь"
      />
    </div>
  )
}
