import { useState, useEffect } from 'react'
import { useBookingStore } from '../store/bookingStore'
import api, { getTelegramUserId, getTelegramUsername, getUserDataFromLastBooking } from '../api/client'
import type { BookingCreate } from '../api/types'
import WebApp from '@twa-dev/sdk'

export default function ContactForm() {
  const { specialist, date, time, nextStep, prevStep } = useBookingStore()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [additionalInfo, setAdditionalInfo] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  console.log('ContactForm render:', { specialist: specialist?.name, date, time })

  // Автозаполнение данных из Telegram и последней записи
  useEffect(() => {
    const userId = getTelegramUserId()
    const username = getTelegramUsername()
    if (username && !name) {
      setName(username)
    }
    console.log('Telegram user:', { userId, username })
    
    // Получаем данные из последней записи
    if (userId) {
      getUserDataFromLastBooking(userId).then(data => {
        if (data.found) {
          if (!name && data.name) {
            setName(data.name)
            console.log('Auto-filled name from last booking:', data.name)
          }
          if (!phone && data.phone) {
            setPhone(data.phone)
            console.log('Auto-filled phone from last booking:', data.phone)
          }
        }
      }).catch(err => console.error('Error loading user data:', err))
    }
    
    // Проверка что дата и время выбраны
    if (!date || !time) {
      console.warn('ContactForm: date or time not selected, redirecting to slots')
      setTimeout(() => {
        prevStep()
      }, 100)
    }
  }, [])

  // Валидация российского номера телефона
  const validatePhone = (phone: string): boolean => {
    // Удаляем все нецифровые символы кроме + в начале
    const cleaned = phone.replace(/[\s\-\(\)]/g, '')
    
    // Проверяем формат +7 или +8
    if (!/^\+7[0-9]{10}$/.test(cleaned) && !/^\+8[0-9]{10}$/.test(cleaned)) {
      return false
    }
    
    // Преобразуем +8 на +7
    const normalized = cleaned.replace(/^\+8/, '+7')
    
    // Проверяем код оператора (не может начинаться с 0, 1, 2, 5 для мобильных)
    const areaCode = normalized.substring(2, 5)
    const area = parseInt(areaCode, 10)
    
    // Основные мобильные коды России
    if (area < 200 || area > 999) {
      return false
    }
    
    return true
  }

  // Форматирование номера при вводе
  const formatPhone = (value: string): string => {
    // Удаляем все нецифровые символы
    let cleaned = value.replace(/[^0-9]/g, '')
    
    // Преобразуем 8 в начале в 7
    if (cleaned.startsWith('8') && cleaned.length === 11) {
      cleaned = '7' + cleaned.substring(1)
    }
    
    // Добавляем +7 в начало
    if (cleaned.startsWith('7')) {
      cleaned = '+7' + cleaned.substring(1)
    } else if (!cleaned.startsWith('+')) {
      cleaned = '+7' + cleaned
    }
    
    // Форматируем: +7 (XXX) XXX-XX-XX
    if (cleaned.length > 3) {
      cleaned = cleaned.substring(0, 3) + ' (' + cleaned.substring(3)
    }
    if (cleaned.length > 7) {
      cleaned = cleaned.substring(0, 7) + ') ' + cleaned.substring(7)
    }
    if (cleaned.length > 12) {
      cleaned = cleaned.substring(0, 12) + '-' + cleaned.substring(12)
    }
    if (cleaned.length > 15) {
      cleaned = cleaned.substring(0, 15) + '-' + cleaned.substring(15)
    }
    
    return cleaned
  }

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value
    const formatted = formatPhone(rawValue)
    setPhone(formatted)
    // Сбрасываем ошибку валидации при изменении
    if (error && error.includes('телефон')) {
      setError(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Проверка что дата и время выбраны
    if (!date || !time) {
      setError('Отсутствует дата или время. Пожалуйста, начните запись заново.')
      setTimeout(() => {
        prevStep()
      }, 2000)
      return
    }
    
    // Валидация номера телефона
    if (!validatePhone(phone)) {
      setError('Введите номер в формате +7 (999) 123-45-67')
      return
    }
    
    if (!name.trim() || !phone.trim()) {
      setError('Пожалуйста, заполните все обязательные поля')
      return
    }

    try {
      setLoading(true)
      setError(null)

      const telegramUserId = getTelegramUserId()
      const telegramUsername = getTelegramUsername()
      
      console.log('Sending booking with Telegram user:', { telegramUserId, telegramUsername })
      console.log('Booking data:', { specialist_id: specialist!.id, date, time, name: name.trim(), phone: phone.trim() })

      const bookingData: BookingCreate = {
        specialist_id: specialist!.id,
        date: date,
        time: time,
        name: name.trim(),
        phone: phone.trim(),
        additional_info: additionalInfo.trim() || undefined,
      }

      // Отправляем user_id и username в headers
      const response = await api.post('/bookings', bookingData, {
        headers: {
          'X-Telegram-User-Id': telegramUserId || '0',
          'X-Telegram-Username': telegramUsername || name.trim(),
        }
      })
      
      console.log('Booking created:', response.data)
      
      // Расширяем окно после успешной отправки
      WebApp.expand()
      
      nextStep()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка при создании записи')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-2 text-gray-900">
        Контактные данные
      </h2>
      <p className="text-sm text-gray-600 mb-4">
        Заполните информацию для записи на консультацию
      </p>

      {/* Информация о записи */}
      <div className="card mb-4 bg-blue-50">
        <h3 className="font-medium text-gray-900 mb-2">Детали записи:</h3>
        <div className="text-sm space-y-1">
          <p><span className="text-gray-600">Специалист:</span> {specialist?.name}</p>
          <p><span className="text-gray-600">Дата:</span> {new Date(date!).toLocaleDateString('ru-RU')}</p>
          <p><span className="text-gray-600">Время:</span> {time}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Имя */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
            Имя <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Введите ваше имя"
            required
          />
        </div>

        {/* Телефон */}
        <div>
          <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
            Телефон <span className="text-red-500">*</span>
          </label>
          <input
            type="tel"
            id="phone"
            value={phone}
            onChange={handlePhoneChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="+7 (999) 123-45-67"
            required
          />
        </div>

        {/* Дополнительная информация */}
        <div>
          <label htmlFor="additionalInfo" className="block text-sm font-medium text-gray-700 mb-1">
            Комментарий (необязательно)
          </label>
          <textarea
            id="additionalInfo"
            value={additionalInfo}
            onChange={(e) => setAdditionalInfo(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={3}
            placeholder="Дополнительная информация или вопросы"
          />
        </div>

        {/* Ошибка */}
        {error && (
          <div className="text-red-500 text-sm bg-red-50 p-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Кнопки */}
        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={prevStep}
            className="btn-secondary flex-1"
          >
            Назад
          </button>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary flex-1 disabled:opacity-50"
          >
            {loading ? 'Отправка...' : 'Продолжить'}
          </button>
        </div>
      </form>
    </div>
  )
}
