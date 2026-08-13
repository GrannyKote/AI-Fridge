import { Link } from 'react-router-dom'
import { ArrowLeftIcon, LogoMark } from './icons.jsx'
import '../styles/auth.css'

export function AuthLayout({ title, subtitle, backTo, children }) {
  return (
    <div className="auth">
      <div className="auth__card">
        <header className="auth__head">
          {backTo ? (
            <Link className="auth__back" to={backTo}>
              <ArrowLeftIcon />
              Назад
            </Link>
          ) : (
            <LogoMark className="auth__logo" />
          )}

          <h1 className="auth__title">{title}</h1>
          <p className="auth__subtitle">{subtitle}</p>
        </header>

        {children}
      </div>
    </div>
  )
}
