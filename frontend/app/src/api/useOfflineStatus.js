import { useEffect, useState } from 'react'
import { offlineStatus, subscribeOffline } from './offlineStore.js'

export function useOfflineStatus(user) {
  const [status, setStatus] = useState(() => offlineStatus(user))
  useEffect(() => {
    const update = () => setStatus(offlineStatus(user))
    update()
    return subscribeOffline(update)
  }, [user])
  return status
}
