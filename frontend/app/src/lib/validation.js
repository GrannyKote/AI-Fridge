const LOGIN_PATTERN = /^[a-zA-Z0-9._-]+$/

export const LOGIN_MIN = 3
export const LOGIN_MAX = 20
export const PASSWORD_MIN = 6

export function validateLogin(login) {
  const value = login.trim()

  if (!value) {
    return 'Введите логин'
  }
  if (value.length < LOGIN_MIN) {
    return `Минимум ${LOGIN_MIN} символа`
  }
  if (value.length > LOGIN_MAX) {
    return `Максимум ${LOGIN_MAX} символов`
  }
  if (!LOGIN_PATTERN.test(value)) {
    return 'Только латиница, цифры и знаки . _ -'
  }

  return ''
}

export function validateRequired(value, message) {
  return value.trim() ? '' : message
}

export function validatePassword(password) {
  if (!password) {
    return 'Введите пароль'
  }
  if (password.length < PASSWORD_MIN) {
    return `Минимум ${PASSWORD_MIN} символов`
  }

  return ''
}

export function validatePasswordRepeat(password, repeat) {
  if (!repeat) {
    return 'Повторите пароль'
  }
  if (password !== repeat) {
    return 'Пароли не совпадают'
  }

  return ''
}

export function hasErrors(errors) {
  return Object.values(errors).some(Boolean)
}
