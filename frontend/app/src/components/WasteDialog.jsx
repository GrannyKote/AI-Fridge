import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { AmountField } from './AmountField.jsx'
import { FormAlert } from './FormAlert.jsx'
import { amountError, parseAmount } from '../lib/pantry.js'
import '../styles/dialog.css'

const REASONS = [
  { value: 'spoiled', title: 'Продукт испортился' },
  { value: 'mistake', title: 'Продукт добавлен ошибочно' },
]

export function WasteDialog({ groupId, product, onClose, onWasted }) {
  const [reason, setReason] = useState('spoiled')
  const [quantity, setQuantity] = useState('')
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  const available = Number(product.remaining ?? product.quantity)

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

    const spoiled = reason === 'spoiled'
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
        <h2 className="dialog__title">Списать продукт</h2>
        <p className="dialog__subtitle">{product.name}</p>

        <form className="form" onSubmit={handleSubmit} noValidate>
          <fieldset className="radios">
            <legend className="field__label">Причина списания</legend>

            {REASONS.map((option) => (
              <div className="radio" key={option.value}>
                <label className="radio__option">
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

                {option.value === 'spoiled' && reason === 'spoiled' && (
                  <div className="radio__extra">
                    <AmountField
                      id="waste-quantity"
                      value={quantity}
                      onChange={(value) => {
                        setQuantity(value)
                        setError('')
                      }}
                      unit={product.unit}
                      available={available}
                      error={error}
                    />
                  </div>
                )}
              </div>
            ))}
          </fieldset>

          <FormAlert>{formError}</FormAlert>

          <div className="dialog__actions">
            <button className="btn btn--ghost" type="button" onClick={onClose}>
              Отмена
            </button>
            <button className="btn btn--primary" type="submit" disabled={pending}>
              {pending ? 'Списываем...' : 'Списать'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
