import axios from 'axios'

// API base URL (в продакшене заменить на реальный домен)
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Добавление init_data из Telegram WebApp
export const setAuthData = (initData: string) => {
  api.defaults.headers.common['Authorization'] = `TelegramWebApp ${initData}`
}

export default api
