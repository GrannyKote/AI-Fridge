import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { QuantityPicker, ProductHead } from './QuantityPicker.jsx'
import { actionAmount, amountError, parseAmount } from '../lib/pantry.js'
import '../styles/dialog.css'

export function ConsumeDialog({ groupId, product, onClose, onConsumed }) {
  const [quantity, setQuantity] = useState('')
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  const available = Number(product.remaining ?? product.quantity)
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

    const nextError = amountError(quantity, available, product.unit)
    setError(nextError)

    if (nextError) {
      return
    }

    setPending(true)
    try {
      const updated = await pantryApi.consumeProduct(groupId, product.id, parseAmount(quantity))
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

        <form className="form" onSubmit={handleSubmit} noValidate>
          <ProductHead product={product} available={available} />

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
          />

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Записываем...' : summary ? `Употребить ${summary}` : 'Употребить'}
          </button>
        </form>
      </div>
    </div>
  )
}
