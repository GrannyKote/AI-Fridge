import { LogoMark } from '../components/icons.jsx'
import { useAuth } from '../auth/useAuth.js'
import '../styles/auth.css'
import '../styles/home.css'

export default function HomePage() {
  const { user, signOut } = useAuth()
  const group = user.groups?.[0]

  return (
    <div className="auth">
      <div className="auth__card home">
        <LogoMark className="auth__logo" />

        <div>
          <h1 className="auth__title">Привет, {user.login}!</h1>
          <p className="auth__subtitle">
            Вы вошли в AI-Fridge. Здесь появится кладовая с продуктами и сроками годности.
          </p>
          {group && <p className="home__group">Группа: {group.name}</p>}
        </div>

        <button className="btn btn--ghost" type="button" onClick={signOut}>
          Выйти
        </button>
      </div>
    </div>
  )
}
