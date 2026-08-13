import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { AmountField } from './AmountField.jsx'
import { FormAlert } from './FormAlert.jsx'
import { amountError, parseAmount } from '../lib/pantry.js'
import '../styles/dialog.css'

export function ConsumeDialog({ groupId, product, onClose, onConsumed }) {
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

    const nextError = amountError(quantity, available, product.unit)
    setError(nextError)

    if (nextError) {
      return
    }

    setPending(true)
    try {
      const updated = await pantryApi.consumeProduct(
        groupId,
        product.id,
        parseAmount(quantity),
      )
      onConsumed(updated)
    } catch (consumeError) {
      setFormError(consumeError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Употребить продукт">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />
        <h2 className="dialog__title">Употребить продукт</h2>
        <p className="dialog__subtitle">{product.name}</p>

        <form className="form" onSubmit={handleSubmit} noValidate>
          <AmountField
            id="consume-quantity"
            value={quantity}
            onChange={(value) => {
              setQuantity(value)
              setError('')
            }}
            unit={product.unit}
            available={available}
            error={error}
            autoFocus
          />

          <FormAlert>{formError}</FormAlert>

          <div className="dialog__actions">
            <button className="btn btn--ghost" type="button" onClick={onClose}>
              Отмена
            </button>
            <button className="btn btn--primary" type="submit" disabled={pending}>
              {pending ? 'Записываем...' : 'Употребить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
