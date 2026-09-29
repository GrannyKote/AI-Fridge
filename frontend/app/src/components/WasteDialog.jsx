import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { QuantityPicker, ProductHead } from './QuantityPicker.jsx'
import { actionAmount, amountError, formatNumber, parseAmount } from '../lib/pantry.js'
import '../styles/dialog.css'

const REASONS = [
  { value: 'spoiled', title: 'Продукт испортился' },
  { value: 'mistake', title: 'Продукт добавлен ошибочно' },
]

export function WasteDialog({ groupId, product, onClose, onWasted }) {
  const available = Number(product.remaining ?? product.quantity)

  const [reason, setReason] = useState('spoiled')
  // Испорченный продукт обычно выбрасывают целиком, поэтому подставляем весь остаток.
  const [quantity, setQuantity] = useState(() => formatNumber(available))
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  const spoiled = reason === 'spoiled'
  const summary = actionAmount(quantity, product.unit)

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const nextError = spoiled ? amountError(quantity, available, product.unit) : ''
    setError(nextError)

    if (nextError) {
      return
    }

    setPending(true)
    try {
      const updated = await pantryApi.wasteProduct(groupId, product.id, {
        reason,
        quantity: spoiled ? parseAmount(quantity) : null,
      })
      onWasted(updated, reason)
    } catch (wasteError) {
      setFormError(wasteError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Списать продукт">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <form className="form" onSubmit={handleSubmit} noValidate>
          <ProductHead product={product} available={available} />

          <fieldset className="radios">
            <legend className="writeoff__label">Причина списания</legend>

            {REASONS.map((option) => (
              <label className="radio__option" key={option.value}>
                <input
                  className="radio__input"
                  type="radio"
                  name="waste-reason"
                  value={option.value}
                  checked={reason === option.value}
                  onChange={() => {
                    setReason(option.value)
                    setError('')
                  }}
                />
                <span>{option.title}</span>
              </label>
            ))}
          </fieldset>

          {spoiled ? (
            <QuantityPicker
              product={product}
              available={available}
              value={quantity}
              onChange={(value) => {
                setQuantity(value)
                setError('')
              }}
              label="Сколько списать?"
              error={error}
              showTrack={false}
            />
          ) : (
            <p className="writeoff__note">Запись скроется из кладовой, количество списывать не нужно.</p>
          )}

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending
              ? 'Списываем...'
              : spoiled && summary
                ? `Списать ${summary}`
                : 'Списать'}
          </button>
        </form>
      </div>
    </div>
  )
}
