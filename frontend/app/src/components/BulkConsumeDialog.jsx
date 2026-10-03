import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { categoryView, displayProductName, formatAmount } from '../lib/pantry.js'
import { FormAlert } from './FormAlert.jsx'
import '../styles/dialog.css'

export function BulkConsumeDialog({ groupId, products, onClose, onDone }) {
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

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
    setPending(true)

    try {
      for (const product of products) {
        const remaining = Number(product.remaining ?? product.quantity)
        await pantryApi.consumeProduct(groupId, product.id, remaining)
      }
      onDone(products.length)
    } catch (consumeError) {
      setFormError(consumeError.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Употребить выбранное">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />

        <form className="form writeoff" onSubmit={handleSubmit} noValidate>
          <h2 className="dialog__title">Употребить выбранное</h2>
          <p className="writeoff__note">Будут списаны все остатки перечисленных продуктов.</p>

          <ul className="bulk-consume__list">
            {products.map((product) => {
              const { emoji, tone } = categoryView(product.category, product.category_id ?? 0)
              const name = displayProductName(product.name)

              return (
                <li className="bulk-consume__row" key={product.id}>
                  <div className={`card__thumb card__thumb--${tone}`} aria-hidden="true">
                    {emoji}
                  </div>
                  <div className="bulk-consume__body">
                    <p className="bulk-consume__name">{name}</p>
                    <p className="writeoff__stock">Остаток: {formatAmount(product)}</p>
                  </div>
                </li>
              )
            })}
          </ul>

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Записываем...' : 'Употребить все'}
          </button>
        </form>
      </div>
    </div>
  )
}
