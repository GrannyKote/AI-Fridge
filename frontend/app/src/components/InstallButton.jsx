import { useEffect, useState } from 'react'
import { DownloadIcon } from './icons.jsx'

export function InstallButton() {
  const [installEvent, setInstallEvent] = useState(null)

  useEffect(() => {
    function handlePrompt(event) {
      event.preventDefault()
      setInstallEvent(event)
    }

    function handleInstalled() {
      setInstallEvent(null)
    }

    window.addEventListener('beforeinstallprompt', handlePrompt)
    window.addEventListener('appinstalled', handleInstalled)

    return () => {
      window.removeEventListener('beforeinstallprompt', handlePrompt)
      window.removeEventListener('appinstalled', handleInstalled)
    }
  }, [])

  if (!installEvent) {
    return null
  }

  async function install() {
    installEvent.prompt()
    await installEvent.userChoice
    setInstallEvent(null)
  }

  return (
    <button className="auth__install" type="button" onClick={install}>
      <DownloadIcon />
      Установить приложение
    </button>
  )
}
