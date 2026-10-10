import axios from 'axios'
import WebApp from '@twa-dev/sdk'

// API base URL
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '/api'

console.log('API_BASE_URL:', API_BASE_URL)

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Логирование запросов
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.config?.url, error.message)
    return Promise.reject(error)
  }
)

// Получение user_id из Telegram WebApp
export function getTelegramUserId(): number | null {
  try {
    const initData = WebApp.initData
    const urlParams = new URLSearchParams(initData)
    const userParam = urlParams.get('user')
    if (userParam) {
      const user = JSON.parse(userParam)
      return user.id || null
    }
  } catch (e) {
    console.error('Failed to parse Telegram init data:', e)
  }
  return null
}

// Получение username из Telegram WebApp
export function getTelegramUsername(): string | null {
  try {
    const initData = WebApp.initData
    const urlParams = new URLSearchParams(initData)
    const userParam = urlParams.get('user')
    if (userParam) {
      const user = JSON.parse(userParam)
      return user.username || user.first_name || null
    }
  } catch (e) {
    console.error('Failed to parse Telegram init data:', e)
  }
  return null
}

export default api
