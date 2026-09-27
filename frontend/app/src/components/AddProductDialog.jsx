import { useEffect, useRef, useState } from 'react'
import { pantryApi, receiptApi } from '../api/client.js'
import { FormAlert } from './FormAlert.jsx'
import { SuggestInput } from './SuggestInput.jsx'
import {
  ArrowLeftIcon,
  CabinetIcon,
  CameraIcon,
  CanIcon,
  HouseIcon,
  IceIcon,
  MicIcon,
  PencilIcon,
  SnowflakeIcon,
  SpiceIcon,
} from './icons.jsx'
import '../styles/dialog.css'

const EMPTY_FORM = {
  name: '',
  productId: null,
  category: '',
  unitId: '',
  quantity: '1',
  purchasedAt: today(),
  bestBefore: '',
  placeId: '',
}

const METHODS = [
  { key: 'manual', title: 'Вручную', icon: <PencilIcon /> },
  { key: 'receipt', title: 'Чек', icon: <CameraIcon /> },
  { key: 'voice', title: 'Голос', icon: <MicIcon /> },
]

const PLACE_ICONS = {
  Холодильник: <SnowflakeIcon />,
  Морозилка: <IceIcon />,
  Бакалея: <HouseIcon />,
  Шкаф: <CabinetIcon />,
  Специи: <SpiceIcon />,
  Консервы: <CanIcon />,
}

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

function today() {
  return new Date().toISOString().slice(0, 10)
}

function placeIdOf(places, name, category) {
  const wanted = PLACE_BY_NAME[name] || PLACE_BY_CATEGORY[category] || 'Шкаф'
  return String(places.find((place) => place.name === wanted)?.id ?? places[0]?.id ?? '')
}

export function AddProductDialog({ groupId, categories, onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [method, setMethod] = useState('manual')
  const [units, setUnits] = useState([])
  const [places, setPlaces] = useState([])
  const [nameSuggestions, setNameSuggestions] = useState([])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [pending, setPending] = useState(false)
  const [placeTouched, setPlaceTouched] = useState(false)
  const [drafts, setDrafts] = useState([])
  const [recording, setRecording] = useState(false)
  const cameraRef = useRef(null)
  const libraryRef = useRef(null)
  const audioRef = useRef(null)
  const kindRef = useRef('receipt')
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const discardRef = useRef(false)

  useEffect(() => {
    let cancelled = false

    Promise.all([pantryApi.units(), pantryApi.places()])
      .then(([unitList, placeList]) => {
        if (cancelled) {
          return
        }

        setUnits(unitList)
        setPlaces(placeList)
        setForm((current) => ({
          ...current,
          unitId: current.unitId || String(unitList.find((unit) => unit.name === 'шт')?.id ?? ''),
          placeId: current.placeId || placeIdOf(placeList, current.name, current.category),
        }))
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

  useEffect(() => {
    const query = form.name.trim()

    if (method !== 'manual' || query.length < 1) {
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
  }, [form.name, method])

  function update(patch) {
    setForm((current) => {
      const next = { ...current, ...patch }

      if (!placeTouched && places.length > 0 && ('name' in patch || 'category' in patch)) {
        next.placeId = placeIdOf(places, next.name.trim(), next.category)
      }

      return next
    })
  }

  function clearError(field) {
    setErrors((current) => ({ ...current, [field]: '' }))
  }

  function releaseMic() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  function cancelVoice() {
    discardRef.current = true
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
      return
    }
    discardRef.current = false
    releaseMic()
    setRecording(false)
  }

  useEffect(() => {
    return () => {
      discardRef.current = true
      if (recorderRef.current && recorderRef.current.state !== 'inactive') {
        recorderRef.current.stop()
      }
      releaseMic()
    }
  }, [])

  function pickFile(input) {
    if (!input) {
      return
    }
    input.value = ''
    input.click()
  }

  function openPhoto(fromLibrary) {
    setMethod('receipt')
    kindRef.current = 'receipt'
    setFormError('')
    pickFile(fromLibrary ? libraryRef.current : cameraRef.current)
  }

  function openAudioFile() {
    setMethod('voice')
    kindRef.current = 'voice'
    setFormError('')
    pickFile(audioRef.current)
  }

  async function startVoice() {
    setMethod('voice')
    kindRef.current = 'voice'
    setFormError('')
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      openAudioFile()
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      streamRef.current = stream
      const mimeType = ['audio/mp4', 'audio/webm', 'audio/ogg'].find((type) =>
        MediaRecorder.isTypeSupported(type),
      )
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunksRef.current = []
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }
      recorder.onstop = () => {
        const discard = discardRef.current
        discardRef.current = false
        const type = recorder.mimeType || 'audio/mp4'
        const blob = new Blob(chunksRef.current, { type })
        releaseMic()
        setRecording(false)
        if (discard || blob.size === 0) {
          return
        }
        const ext = type.includes('webm') ? 'webm' : type.includes('ogg') ? 'ogg' : 'm4a'
        submitFile(new File([blob], `voice.${ext}`, { type }), 'voice')
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      releaseMic()
      setRecording(false)
      setFormError('Микрофон недоступен. Загрузите аудиофайл.')
    }
  }

  function stopVoice() {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
  }

  async function submitFile(file, kind) {
    setPending(true)
    setFormError('')
    try {
      const result = await receiptApi.recognize(groupId, file, kind)
      const items = result.items ?? []
      setDrafts(items)
      if (items.length === 0) {
        setFormError('На записи не нашлось продуктов')
      }
    } catch (error) {
      setDrafts([])
      setFormError(error.message)
    } finally {
      setPending(false)
    }
  }

  function onCapture(event) {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }
    submitFile(file, kindRef.current)
  }

  function validate() {
    const quantity = Number(form.quantity.replace(',', '.'))

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
      const created = await pantryApi.addProduct(groupId, {
        name: form.name.trim(),
        category: form.category,
        unit_id: Number(form.unitId),
        quantity: Number(form.quantity.replace(',', '.')),
        best_before: form.bestBefore,
        storage_place_id: Number(form.placeId),
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
    <div className="dialog dialog--page" role="dialog" aria-modal="true" aria-labelledby="add-title">
      <div className="add">
        <header className="add__head">
          <button className="icon-btn icon-btn--round" type="button" onClick={onClose} aria-label="Назад">
            <ArrowLeftIcon />
          </button>
          <h2 className="add__title" id="add-title">
            Добавить продукт
          </h2>
        </header>

        <div className="method" role="tablist" aria-label="Способ добавления">
          {METHODS.map((item) => (
            <button
              key={item.key}
              className={`method__item${method === item.key ? ' is-active' : ''}`}
              type="button"
              role="tab"
              aria-selected={method === item.key}
              onClick={() => {
                if (item.key === method) {
                  return
                }
                if (recording) {
                  cancelVoice()
                }
                setMethod(item.key)
                setFormError('')
                setDrafts([])
                setErrors((current) => ({ ...current, name: '' }))
                if (item.key !== 'manual') {
                  update({ name: '', productId: null })
                }
              }}
            >
              {item.icon}
              {item.title}
            </button>
          ))}
        </div>

        {method === 'receipt' && (
          <div className="capture">
            <button className="capture__btn" type="button" onClick={() => openPhoto(false)} disabled={pending}>
              Сфотографировать
            </button>
            <button className="capture__btn" type="button" onClick={() => openPhoto(true)} disabled={pending}>
              Из библиотеки
            </button>
          </div>
        )}

        {method === 'voice' && (
          <div className="capture">
            <button
              className={`capture__btn${recording ? ' is-recording' : ''}`}
              type="button"
              onClick={recording ? stopVoice : startVoice}
              disabled={pending}
            >
              {recording ? 'Стоп' : 'Записать'}
            </button>
            <button className="capture__btn" type="button" onClick={openAudioFile} disabled={pending || recording}>
              Загрузить запись
            </button>
          </div>
        )}

        <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={onCapture} />
        <input ref={libraryRef} type="file" accept="image/*" hidden onChange={onCapture} />
        <input ref={audioRef} type="file" accept="audio/*" hidden onChange={onCapture} />

        {method !== 'manual' && pending && <p className="drafts__hint">Разбираем запись...</p>}

        {method !== 'manual' && drafts.length > 0 && (
          <div className="drafts">
            <p className="drafts__hint">Что куплено, сколько и где хранить.</p>
            <div className="drafts__head">
              <span>Куплено</span>
              <span>Сколько</span>
              <span>Хранение</span>
            </div>
            {drafts.map((item, index) => (
              <div key={index} className="drafts__item">
                <span>{item.name}</span>
                <span>
                  {item.quantity} {item.unit}
                </span>
                <span>{item.storage || 'Шкаф'}</span>
              </div>
            ))}
          </div>
        )}

        {method !== 'manual' && <FormAlert>{formError}</FormAlert>}

        {method === 'manual' && (
        <form className="form add__form" onSubmit={handleSubmit} noValidate>
          <SuggestInput
              label="Название"
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
          </div>

          <div className="dialog__row">
            <div className="field">
              <label className="field__label" htmlFor="purchased-at">
                Дата покупки
              </label>
              <div className="field__control">
                <input
                  id="purchased-at"
                  className="field__input"
                  type="date"
                  value={form.purchasedAt}
                  onChange={(event) => update({ purchasedAt: event.target.value })}
                />
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
        )}
      </div>
    </div>
  )
}
