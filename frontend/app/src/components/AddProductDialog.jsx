import { useCallback, useEffect, useState } from 'react'
import { pantryApi } from '../api/client.js'
import {
  FALLBACK_UNITS,
  dateAfterDays,
  defaultBestBeforeOf,
  defaultQuantityForUnit,
  displayProductName,
  formatNumber,
} from '../lib/pantry.js'
import { DateInput } from './DateInput.jsx'
import { FormAlert } from './FormAlert.jsx'
import { SuggestInput } from './SuggestInput.jsx'
import { PLACE_ICONS } from '../lib/placeIcons.jsx'
import {
  ArrowLeftIcon,
  CameraIcon,
  HouseIcon,
  MicIcon,
  MinusIcon,
  PencilIcon,
  PlusIcon,
} from './icons.jsx'
import '../styles/dialog.css'

const EMPTY_FORM = {
  name: '',
  productId: null,
  category: '',
  unitId: '',
  quantity: '1',
  price: '',
  purchasedAt: dateAfterDays(),
  bestBefore: '',
  placeId: '',
}

const METHODS = [
  { key: 'receipt', title: 'Чек', icon: <CameraIcon /> },
  { key: 'voice', title: 'Голос', icon: <MicIcon /> },
  { key: 'manual', title: 'Вручную', icon: <PencilIcon /> },
]

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

function placeIdOf(places, name, category, storagePlaceId = null) {
  if (
    storagePlaceId != null &&
    places.some((place) => String(place.id) === String(storagePlaceId))
  ) {
    return String(storagePlaceId)
  }

  const wanted = PLACE_BY_NAME[name] || PLACE_BY_CATEGORY[category] || 'Шкаф'
  return String(places.find((place) => place.name === wanted)?.id ?? places[0]?.id ?? '')
}

function unitIdOf(units) {
  return String(units.find((unit) => unit.name === 'шт')?.id ?? units[0]?.id ?? '')
}

function defaultAmountOf(product, units) {
  if (product.unit_id == null && product.quantity == null) {
    return null
  }

  const unitId =
    product.unit_id != null ? String(product.unit_id) : unitIdOf(units)
  const unit = units.find((item) => String(item.id) === unitId)
  const quantity =
    product.quantity != null
      ? formatNumber(product.quantity)
      : defaultQuantityForUnit(unit?.name)

  return { unitId, quantity }
}

function applyCatalogAmount(patch, product, units, amountTouched) {
  if (amountTouched) {
    return patch
  }

  const amount = defaultAmountOf(product, units)
  if (!amount) {
    return patch
  }

  return { ...patch, unitId: amount.unitId, quantity: amount.quantity }
}

function catalogUnitsOf(units) {
  return units.length > 0 ? units : FALLBACK_UNITS
}

function suggestionOf(product, key) {
  return {
    key,
    label: displayProductName(product.name),
    meta: product.category ?? '',
    product,
  }
}

function formFromProduct(product, units, places) {
  const remaining = product.remaining ?? product.quantity

  return {
    name: displayProductName(product.name),
    productId: product.product_id ?? null,
    category: product.category ?? '',
    unitId: String(product.unit_id ?? unitIdOf(units)),
    quantity: formatNumber(remaining),
    price:
      product.price === null || product.price === undefined || product.price === ''
        ? ''
        : formatNumber(product.price),
    purchasedAt: dateAfterDays(),
    bestBefore: product.best_before ?? '',
    placeId: String(
      places.length > 0
        ? placeIdOf(places, product.name, product.category, product.storage_place_id)
        : '',
    ),
  }
}

function localSuggestions(products, query) {
  const seen = new Set()
  const items = []

  for (const product of products) {
    const name = product.name?.trim()
    const key = name?.toLowerCase()

    if (!name || seen.has(key)) {
      continue
    }

    seen.add(key)
    items.push(
      suggestionOf(
        {
          name,
          category: product.category ?? '',
          expires_in: product.expires_in,
          storage_place_id: product.storage_place_id,
        },
        `local-${key}`,
      ),
    )
  }

  const prefix = query.trim().toLowerCase()
  return (prefix ? items.filter((item) => item.label.toLowerCase().startsWith(prefix)) : items).slice(
    0,
    12,
  )
}

export function AddProductDialog({
  groupId,
  categories,
  products = [],
  units: unitsProp = [],
  places: placesProp = [],
  editProduct = null,
  onClose,
  onCreated,
  onUpdated,
}) {
  const isEdit = editProduct != null
  const initialUnits = catalogUnitsOf(unitsProp)
  const [form, setForm] = useState(() =>
    isEdit
      ? formFromProduct(editProduct, initialUnits, placesProp)
      : {
          ...EMPTY_FORM,
          unitId: unitIdOf(initialUnits),
          placeId: placesProp.length > 0 ? placeIdOf(placesProp, '', '') : '',
        },
  )
  const [method, setMethod] = useState('receipt')
  const [units, setUnits] = useState(initialUnits)
  const [places, setPlaces] = useState(placesProp)
  const [nameSuggestions, setNameSuggestions] = useState([])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)
  const [placeTouched, setPlaceTouched] = useState(isEdit)
  const [bestBeforeTouched, setBestBeforeTouched] = useState(isEdit)
  const [amountTouched, setAmountTouched] = useState(isEdit)

  useEffect(() => {
    let cancelled = false
    const unitsReady = unitsProp.length > 0
    const placesReady = placesProp.length > 0

    if (unitsReady && placesReady) {
      return undefined
    }

    Promise.all([
      unitsReady ? Promise.resolve(unitsProp) : pantryApi.units().catch(() => FALLBACK_UNITS),
      placesReady ? Promise.resolve(placesProp) : pantryApi.places(),
    ])
      .then(([unitList, placeList]) => {
        if (cancelled) {
          return
        }

        const nextUnits = catalogUnitsOf(unitList)
        setUnits(nextUnits)
        setPlaces(placeList)
        setForm((current) => ({
          ...current,
          unitId: current.unitId || unitIdOf(nextUnits),
          placeId: current.placeId || placeIdOf(placeList, current.name, current.category),
        }))
      })
      .catch((error) => setFormError(error.message))

    return () => {
      cancelled = true
    }
  }, [unitsProp, placesProp])

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const update = useCallback((patch) => {
    setForm((current) => {
      const next = { ...current, ...patch }

      if (!placeTouched && places.length > 0 && ('name' in patch || 'category' in patch)) {
        next.placeId = placeIdOf(
          places,
          next.name.trim(),
          next.category,
          'storage_place_id' in patch ? patch.storage_place_id : undefined,
        )
      }

      return next
    })
  }, [placeTouched, places])

  const clearError = useCallback((field) => {
    setErrors((current) => ({ ...current, [field]: '' }))
  }, [])

  useEffect(() => {
    const query = form.name.trim()

    if (!query) {
      setNameSuggestions([])
      return undefined
    }

    setNameSuggestions(localSuggestions(products, query))

    const timer = setTimeout(async () => {
      try {
        const found = await pantryApi.searchProducts(query)
        if (found.length > 0) {
          setNameSuggestions(found.map((product) => suggestionOf(product, product.id)))
        }
      } catch {
        setNameSuggestions(localSuggestions(products, query))
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [form.name, products])

  useEffect(() => {
    if (bestBeforeTouched) {
      return
    }

    const typed = form.name.trim().toLowerCase()
    const match = nameSuggestions.find(
      (item) => item.label.trim().toLowerCase() === typed,
    )
    const next = defaultBestBeforeOf(match?.product)

    if (!next || (form.bestBefore === next && form.productId === (match.product.id ?? null))) {
      return
    }

    const patch = {
      bestBefore: next,
      productId: match.product.id ?? null,
      category: match.product.category ?? form.category,
    }

    if (!placeTouched && places.length > 0) {
      patch.placeId = placeIdOf(
        places,
        form.name.trim(),
        patch.category,
        match.product.storage_place_id,
      )
    }

    Object.assign(patch, applyCatalogAmount({}, match.product, units, amountTouched))

    update(patch)
    clearError('bestBefore')
    clearError('category')
    if (patch.unitId) {
      clearError('unitId')
    }
    if (patch.quantity) {
      clearError('quantity')
    }
  }, [
    nameSuggestions,
    bestBeforeTouched,
    placeTouched,
    amountTouched,
    units,
    places,
    form.name,
    form.bestBefore,
    form.productId,
    form.category,
    update,
    clearError,
  ])

  function validate() {
    const quantity = Number(form.quantity.replace(',', '.'))
    const price = Number(form.price.replace(',', '.'))

    return {
      name: form.name.trim() ? '' : 'Введите название',
      category: form.category ? '' : 'Выберите категорию',
      unitId: form.unitId ? '' : 'Выберите единицу',
      quantity:
        form.quantity.trim() === ''
          ? 'Введите количество'
          : Number.isFinite(quantity) && quantity > 0
            ? ''
            : 'Количество должно быть больше нуля',
      // Цена необязательна, но если её ввели — должна быть неотрицательным числом.
      price:
        form.price.trim() === '' || (Number.isFinite(price) && price >= 0)
          ? ''
          : 'Цена должна быть числом не меньше нуля',
      bestBefore: form.bestBefore ? '' : 'Укажите срок годности',
      placeId: form.placeId ? '' : 'Выберите место хранения',
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
      const payload = {
        name: displayProductName(form.name),
        category: form.category,
        unit_id: Number(form.unitId),
        quantity: Number(form.quantity.replace(',', '.')),
        price: form.price.trim() === '' ? null : Number(form.price.replace(',', '.')),
        best_before: form.bestBefore,
        // Без явного выбора места сервер берёт product.id_storage_place или эвристику.
        storage_place_id: placeTouched ? Number(form.placeId) : null,
        product_id: form.productId,
      }

      if (isEdit) {
        const updated = await pantryApi.updateProduct(groupId, editProduct.id, payload)
        onUpdated?.(editProduct, updated)
      } else {
        const created = await pantryApi.addProduct(groupId, payload)
        onCreated(created)
      }
    } catch (error) {
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="dialog dialog--page" role="dialog" aria-modal="true" aria-labelledby="add-title">
      <div className="add">
        <header className="add__head">
          <button className="icon-btn icon-btn--round" type="button" onClick={onClose} aria-label="Назад">
            <ArrowLeftIcon />
          </button>
          <h2 className="add__title" id="add-title">
            {isEdit ? 'Редактировать продукт' : 'Добавить продукт'}
          </h2>
        </header>

        {!isEdit && (
          <div className="method" role="tablist" aria-label="Способ добавления">
            {METHODS.map((item) => (
              <button
                key={item.key}
                className={`method__item${method === item.key ? ' is-active' : ''}`}
                type="button"
                role="tab"
                aria-selected={method === item.key}
                onClick={() => {
                  if (item.key === 'manual') {
                    setMethod(item.key)
                    setFormError('')
                    return
                  }

                  setFormError(`Способ «${item.title}» появится позже`)
                }}
              >
                {item.icon}
                {item.title}
              </button>
            ))}
          </div>
        )}

        <form className="form add__form" onSubmit={handleSubmit} noValidate>
          <SuggestInput
            label="Название"
            value={form.name}
            onChange={(value) => {
              update({ name: value, productId: null })
              clearError('name')
            }}
            onPick={({ product }) => {
              const patch = {
                name: displayProductName(product.name),
                productId: product.id ?? null,
                category: product.category ?? '',
              }

              // Справочник знает срок хранения — предлагаем срок годности сами.
              const next = defaultBestBeforeOf(product)
              if (!bestBeforeTouched && next) {
                patch.bestBefore = next
                clearError('bestBefore')
              }

              if (!placeTouched && places.length > 0) {
                patch.placeId = placeIdOf(
                  places,
                  patch.name,
                  patch.category,
                  product.storage_place_id,
                )
              }

              Object.assign(patch, applyCatalogAmount({}, product, units, amountTouched))

              update(patch)
              clearError('name')
              clearError('category')
              if (patch.unitId) {
                clearError('unitId')
              }
              if (patch.quantity) {
                clearError('quantity')
              }
            }}
            suggestions={nameSuggestions}
            error={errors.name}
            placeholder="Начните вводить..."
            autoFocus
          />

          <div className={`field${errors.category ? ' field--invalid' : ''}`}>
            <label className="field__label" htmlFor="category">
              Категория
            </label>
            <div className="field__control">
              <select
                id="category"
                className="field__input field__select"
                value={form.category}
                onChange={(event) => {
                  update({ category: event.target.value })
                  clearError('category')
                }}
              >
                <option value="">Выберите категорию</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.name}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            {errors.category && <p className="field__error">{errors.category}</p>}
          </div>

          <div className="dialog__row">
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
                    setAmountTouched(true)
                    update({ quantity: event.target.value })
                    clearError('quantity')
                  }}
                />
              </div>
              {errors.quantity && <p className="field__error">{errors.quantity}</p>}
            </div>

            <div className={`field${errors.unitId ? ' field--invalid' : ''}`}>
              <label className="field__label" htmlFor="unit">
                Единица
              </label>
              <div className="field__control">
                <select
                  id="unit"
                  className="field__input field__select"
                  value={form.unitId}
                  onChange={(event) => {
                    setAmountTouched(true)
                    const unitId = event.target.value
                    const unit = units.find((item) => String(item.id) === unitId)
                    update(
                      isEdit
                        ? { unitId }
                        : {
                            unitId,
                            quantity: defaultQuantityForUnit(unit?.name),
                          },
                    )
                    clearError('unitId')
                    clearError('quantity')
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
          </div>

          <div className={`field${errors.price ? ' field--invalid' : ''}`}>
            <label className="field__label" htmlFor="price">
              Цена
            </label>
            <div className="field__control">
              <input
                id="price"
                className="field__input field__input--with-suffix"
                type="text"
                inputMode="decimal"
                placeholder="Необязательно"
                value={form.price}
                onChange={(event) => {
                  update({ price: event.target.value })
                  clearError('price')
                }}
              />
              <span className="field__suffix">₽</span>
            </div>
            {errors.price && <p className="field__error">{errors.price}</p>}
          </div>

          <div className="field">
            <label className="field__label" htmlFor="purchased-at">
              Дата покупки
            </label>
            <div className="field__control">
              <DateInput
                id="purchased-at"
                value={form.purchasedAt}
                onChange={(purchasedAt) => update({ purchasedAt })}
              />
            </div>
          </div>

          <div className={`field${errors.bestBefore ? ' field--invalid' : ''}`}>
            <label className="field__label" htmlFor="best-before">
              Срок годности
            </label>
            <div className="field__control field__stepper">
              <button
                className="stepper"
                type="button"
                onClick={() => {
                  setBestBeforeTouched(true)
                  update({ bestBefore: dateAfterDays(-1, form.bestBefore) })
                  clearError('bestBefore')
                }}
                aria-label="На день раньше"
              >
                <MinusIcon />
              </button>
              <DateInput
                id="best-before"
                value={form.bestBefore}
                onChange={(bestBefore) => {
                  setBestBeforeTouched(true)
                  update({ bestBefore })
                  clearError('bestBefore')
                }}
              />
              <button
                className="stepper"
                type="button"
                onClick={() => {
                  setBestBeforeTouched(true)
                  update({ bestBefore: dateAfterDays(1, form.bestBefore) })
                  clearError('bestBefore')
                }}
                aria-label="На день позже"
              >
                <PlusIcon />
              </button>
            </div>
            {errors.bestBefore && <p className="field__error">{errors.bestBefore}</p>}
          </div>

          <fieldset className={`places${errors.placeId ? ' field--invalid' : ''}`}>
            <legend className="field__label">Хранение</legend>
            <div className="places__grid">
              {places.map((place) => (
                <button
                  key={place.id}
                  className={`place${String(place.id) === String(form.placeId) ? ' is-active' : ''}`}
                  type="button"
                  onClick={() => {
                    setPlaceTouched(true)
                    update({ placeId: String(place.id) })
                    clearError('placeId')
                  }}
                >
                  <span className="place__icon" aria-hidden="true">
                    {PLACE_ICONS[place.name] ?? <HouseIcon />}
                  </span>
                  {place.name}
                </button>
              ))}
            </div>
            {errors.placeId && <p className="field__error">{errors.placeId}</p>}
          </fieldset>

          <FormAlert>{formError}</FormAlert>

          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? 'Сохраняем...' : 'Сохранить'}
          </button>
        </form>
      </div>
    </div>
  )
}
