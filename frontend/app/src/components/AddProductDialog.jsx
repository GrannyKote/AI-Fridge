import { useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { SuggestInput } from './SuggestInput.jsx'
import '../styles/dialog.css'

const EMPTY_FORM = {
  name: '',
  productId: null,
  category: '',
  unitId: '',
  quantity: '',
  bestBefore: '',
}

export function AddProductDialog({ groupId, categories, onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [units, setUnits] = useState([])
  const [nameSuggestions, setNameSuggestions] = useState([])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    let cancelled = false

    pantryApi
      .units()
      .then((list) => {
        if (!cancelled) {
          setUnits(list)
        }
      })
      .catch((error) => setFormError(error.message))

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // Подсказки по названию — из таблицы product, с задержкой, чтобы не слать
  // запрос на каждое нажатие клавиши.
  useEffect(() => {
    const query = form.name.trim()

    if (query.length < 1) {
      setNameSuggestions([])
      return undefined
    }

    const timer = setTimeout(async () => {
      try {
        const found = await pantryApi.searchProducts(query)
        setNameSuggestions(
          found.map((product) => ({
            key: product.id,
            label: product.name,
            meta: product.category ?? '',
            product,
          })),
        )
      } catch {
        setNameSuggestions([])
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [form.name])

  const categorySuggestions = categories
    .filter((category) =>
      category.name.toLowerCase().startsWith(form.category.trim().toLowerCase()),
    )
    .slice(0, 5)
    .map((category) => ({ key: category.id, label: category.name }))

  function update(patch) {
    setForm((current) => ({ ...current, ...patch }))
  }

  function clearError(field) {
    setErrors((current) => ({ ...current, [field]: '' }))
  }

  function validate() {
    const quantity = Number(form.quantity.replace(',', '.'))

    return {
      name: form.name.trim() ? '' : 'Введите наименование',
      category: form.category.trim() ? '' : 'Укажите категорию',
      unitId: form.unitId ? '' : 'Выберите единицу измерения',
      quantity:
        form.quantity.trim() === ''
          ? 'Введите количество'
          : Number.isFinite(quantity) && quantity > 0
            ? ''
            : 'Количество должно быть больше нуля',
      bestBefore: form.bestBefore ? '' : 'Укажите срок годности',
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const nextErrors = validate()
    setErrors(nextErrors)

    if (Object.values(nextErrors).some(Boolean)) {
      return
    }

    setPending(true)
    try {
      const created = await pantryApi.addProduct(groupId, {
        name: form.name.trim(),
        category: form.category.trim(),
        unit_id: Number(form.unitId),
        quantity: Number(form.quantity.replace(',', '.')),
        best_before: form.bestBefore,
        product_id: form.productId,
      })
      onCreated(created)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog" role="dialog" aria-modal="true" aria-label="Добавить продукт">
      <button className="dialog__backdrop" type="button" onClick={onClose} aria-label="Закрыть" />

      <div className="dialog__sheet">
        <div className="dialog__grabber" aria-hidden="true" />
        <h2 className="dialog__title">Добавить продукт</h2>

        <form className="form" onSubmit={handleSubmit} noValidate>
          <SuggestInput
            label="Наименование"
            value={form.name}
            onChange={(value) => {
              update({ name: value, productId: null })
              clearError('name')
            }}
            onPick={({ product }) => {
              update({
                name: product.name,
                productId: product.id,
                category: product.category ?? '',
              })
              clearError('name')
              clearError('category')
            }}
            suggestions={nameSuggestions}
            error={errors.name}
            hint="Начните вводить название — предложим то, что уже есть в справочнике"
            placeholder="Например, Кефир 2.5%"
            autoFocus
          />

          <SuggestInput
            label="Категория"
            value={form.category}
            onChange={(value) => {
              update({ category: value })
              clearError('category')
            }}
            onPick={({ label }) => {
              update({ category: label })
              clearError('category')
            }}
            suggestions={categorySuggestions}
            error={errors.category}
            placeholder="Например, Молочные"
          />

          <div className="dialog__row">
            <div className={`field${errors.unitId ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor="unit">
                Единицы измерения
              </label>
              <div className="field__control">
                <select
                  id="unit"
                  className="field__input field__select"
                  value={form.unitId}
                  onChange={(event) => {
                    update({ unitId: event.target.value })
                    clearError('unitId')
                  }}
                >
                  <option value="">Выберите</option>
                  {units.map((unit) => (
                    <option key={unit.id} value={unit.id}>
                      {unit.name}
                    </option>
                  ))}
                </select>
              </div>
              {errors.unitId && <p className="field__error">{errors.unitId}</p>}
            </div>

            <div className={`field${errors.quantity ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor="quantity">
                Количество
              </label>
              <div className="field__control">
                <input
                  id="quantity"
                  className="field__input"
                  type="text"
                  inputMode="decimal"
                  value={form.quantity}
                  onChange={(event) => {
                    update({ quantity: event.target.value })
                    clearError('quantity')
                  }}
                  placeholder="0"
                />
              </div>
              {errors.quantity && <p className="field__error">{errors.quantity}</p>}
            </div>
          </div>

          <div className={`field${errors.bestBefore ? ' field--invalid' : ''}`}>
            <label className="field__label" htmlFor="best-before">
              Срок годности
            </label>
            <div className="field__control">
              <input
                id="best-before"
                className="field__input"
                type="date"
                value={form.bestBefore}
                onChange={(event) => {
                  update({ bestBefore: event.target.value })
                  clearError('bestBefore')
                }}
              />
            </div>
            {errors.bestBefore && <p className="field__error">{errors.bestBefore}</p>}
          </div>

          <FormAlert>{formError}</FormAlert>

          <div className="dialog__actions">
            <button className="btn btn--ghost" type="button" onClick={onClose}>
              Отмена
            </button>
            <button className="btn btn--primary" type="submit" disabled={pending}>
              {pending ? 'Добавляем...' : 'Добавить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
