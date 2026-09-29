import { useEffect, useState } from 'react'
import { pantryApi, shoppingApi } from '../api/client.js'
import { useAuth } from '../auth/useAuth.js'
import { formatNumber } from '../lib/pantry.js'
import { DateField } from './DateField.jsx'
import { FormAlert } from './FormAlert.jsx'
import { ArrowLeftIcon, CheckIcon } from './icons.jsx'
import '../styles/dialog.css'
import '../styles/shopping.css'

const PLACE_BY_NAME = {
  'Фарш говяжий': 'Морозилка',
  'Куриное филе': 'Морозилка',
}

const PLACE_BY_CATEGORY = {
  Молочные: 'Холодильник',
  Яйца: 'Холодильник',
  'Мясо и рыба': 'Холодильник',
  'Хлеб и выпечка': 'Шкаф',
  'Крупы и макароны': 'Бакалея',
  'Соусы и специи': 'Специи',
}

function placeIdOf(places, name, category) {
  const wanted = PLACE_BY_NAME[name] || PLACE_BY_CATEGORY[category] || 'Шкаф'
  return String(places.find((place) => place.name === wanted)?.id ?? places[0]?.id ?? '')
}

function toRows(items, places) {
  return items.map((item) => ({
    id: item.id,
    name: item.name,
    category: item.category,
    unit: item.unit ?? '',
    quantity: formatNumber(item.quantity),
    bestBefore: '',
    placeId: places.length ? placeIdOf(places, item.name, item.category) : '',
    checked: true,
    errors: {},
  }))
}

export function CheckoutDialog({ groupId, items, onClose, onDone }) {
  const { user } = useAuth()
  const [places, setPlaces] = useState([])
  const [rows, setRows] = useState(() => toRows(items, []))
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

  useEffect(() => {
    let cancelled = false

    pantryApi
      .places()
      .then((list) => {
        if (cancelled) {
          return
        }

        setPlaces(list)
        setRows((current) =>
          current.map((row) => ({
            ...row,
            placeId: row.placeId || placeIdOf(list, row.name, row.category),
          })),
        )
      })
      .catch((error) => setFormError(error.message))

    return () => {
      cancelled = true
    }
  }, [])

  function patchRow(id, patch) {
    setRows((current) => current.map((row) => (row.id === id ? { ...row, ...patch } : row)))
  }

  function validate() {
    const selected = rows.filter((row) => row.checked)

    if (selected.length === 0) {
      return 'Отметьте товары, которые нужно добавить в кладовую'
    }

    let valid = true
    const nextRows = rows.map((row) => {
      if (!row.checked) {
        return { ...row, errors: {} }
      }

      const quantity = Number(String(row.quantity).replace(',', '.'))
      const errors = {
        quantity:
          String(row.quantity).trim() === ''
            ? 'Введите количество'
            : Number.isFinite(quantity) && quantity > 0
              ? ''
              : 'Количество должно быть больше нуля',
        bestBefore: row.bestBefore ? '' : 'Укажите срок годности',
        placeId: row.placeId ? '' : 'Выберите место хранения',
      }

      if (Object.values(errors).some(Boolean)) {
        valid = false
      }

      return { ...row, errors }
    })

    setRows(nextRows)
    return valid ? '' : 'Проверьте отмеченные товары'
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    const message = validate()
    if (message) {
      setFormError(message)
      return
    }

    setPending(true)
    try {
      await shoppingApi.checkout(
        groupId,
        rows
          .filter((row) => row.checked)
          .map((row) => ({
            id: row.id,
            quantity: Number(String(row.quantity).replace(',', '.')),
            best_before: row.bestBefore,
            storage_place_id: Number(row.placeId),
          })),
        user?.id,
      )
      onDone(rows.filter((row) => row.checked).length)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog dialog--page" role="dialog" aria-modal="true" aria-labelledby="checkout-title">
      <div className="add">
        <header className="add__head">
          <button className="icon-btn icon-btn--round" type="button" onClick={onClose} aria-label="Назад">
            <ArrowLeftIcon />
          </button>
          <h2 className="add__title" id="checkout-title">
            Рассчитать покупки
          </h2>
        </header>

        <form className="form add__form" onSubmit={handleSubmit} noValidate>
          {rows.map((row) => (
            <article className={`checkout-card${row.checked ? '' : ' is-off'}`} key={row.id}>
              <div className="checkout-card__head">
                <button
                  className={`checkout-card__check${row.checked ? ' is-on' : ''}`}
                  type="button"
                  onClick={() => patchRow(row.id, { checked: !row.checked, errors: {} })}
                  aria-pressed={row.checked}
                  aria-label={row.checked ? `Снять «${row.name}»` : `Отметить «${row.name}»`}
                >
                  {row.checked && <CheckIcon />}
                </button>
                <h3 className="checkout-card__name">{row.name}</h3>
              </div>

              <div className="dialog__row">
                <div className={`field${row.errors.quantity ? ' field--invalid' : ''}`}>
                  <label className="field__label" htmlFor={`qty-${row.id}`}>
                    Количество
                  </label>
                  <div className="field__control">
                    <input
                      id={`qty-${row.id}`}
                      className="field__input field__input--with-suffix"
                      type="text"
                      inputMode="decimal"
                      value={row.quantity}
                      disabled={!row.checked}
                      onChange={(event) =>
                        patchRow(row.id, {
                          quantity: event.target.value,
                          errors: { ...row.errors, quantity: '' },
                        })
                      }
                    />
                    <span className="field__suffix">{row.unit}</span>
                  </div>
                  {row.errors.quantity && <p className="field__error">{row.errors.quantity}</p>}
                </div>

                <div className={`field${row.errors.bestBefore ? ' field--invalid' : ''}`}>
                  <label className="field__label" htmlFor={`bb-${row.id}`}>
                    Срок годности
                  </label>
                  <div className="field__control">
                    <DateField
                      id={`bb-${row.id}`}
                      className="field__input"
                      ariaLabel="Срок годности"
                      value={row.bestBefore}
                      disabled={!row.checked}
                      onChange={(bestBefore) =>
                        patchRow(row.id, {
                          bestBefore,
                          errors: { ...row.errors, bestBefore: '' },
                        })
                      }
                    />
                  </div>
                  {row.errors.bestBefore && <p className="field__error">{row.errors.bestBefore}</p>}
                </div>
              </div>

              <div className={`field${row.errors.placeId ? ' field--invalid' : ''}`}>
                <label className="field__label" htmlFor={`place-${row.id}`}>
                  Место хранения
                </label>
                <div className="field__control">
                  <select
                    id={`place-${row.id}`}
                    className="field__input field__select"
                    value={row.placeId}
                    disabled={!row.checked}
                    onChange={(event) =>
                      patchRow(row.id, {
                        placeId: event.target.value,
                        errors: { ...row.errors, placeId: '' },
                      })
                    }
                  >
                    <option value="">Выберите место</option>
                    {places.map((place) => (
                      <option key={place.id} value={place.id}>
                        {place.name}
                      </option>
                    ))}
                  </select>
                </div>
                {row.errors.placeId && <p className="field__error">{row.errors.placeId}</p>}
              </div>
            </article>
          ))}

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Добавляем...' : 'Добавить'}
          </button>
        </form>
      </div>
    </div>
  )
}
