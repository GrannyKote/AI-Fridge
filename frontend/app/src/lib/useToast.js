import { useEffect, useState } from 'react'

export function useToast(timeout = 2200) {
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!toast) {
      return undefined
    }

    const timer = setTimeout(() => setToast(''), timeout)
    return () => clearTimeout(timer)
  }, [toast, timeout])

  return [toast, setToast]
}
