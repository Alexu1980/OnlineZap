import axios from 'axios'

// API base URL (в продакшене заменить на реальный домен)
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

// Добавление init_data из Telegram WebApp
export const setAuthData = (initData: string) => {
  api.defaults.headers.common['Authorization'] = `TelegramWebApp ${initData}`
}

export default api
