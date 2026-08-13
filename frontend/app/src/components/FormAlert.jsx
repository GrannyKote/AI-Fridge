import { AlertIcon } from './icons.jsx'

export function FormAlert({ children }) {
  if (!children) {
    return null
  }

  return (
    <p className="alert" role="alert">
      <AlertIcon />
      <span>{children}</span>
    </p>
  )
}
