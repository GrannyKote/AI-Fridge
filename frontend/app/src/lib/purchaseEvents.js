import { useEffect } from 'react'

const EVENT = 'ai-fridge:purchase-changed'

export function notifyPurchaseChanged() {
  window.dispatchEvent(new Event(EVENT))
}

export function usePurchaseChanged(onChange) {
  useEffect(() => {
    if (!onChange) {
      return undefined
    }

    window.addEventListener(EVENT, onChange)
    return () => window.removeEventListener(EVENT, onChange)
  }, [onChange])
}
