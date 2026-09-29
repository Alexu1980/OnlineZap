import { useState } from 'react'
import { useBookingStore } from '../store/bookingStore'
import api from '../api/client'
import type { BookingCreate } from '../api/types'

export default function ContactForm() {
  const { specialist, date, time, nextStep, prevStep } = useBookingStore()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [additionalInfo, setAdditionalInfo] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!name.trim() || !phone.trim()) {
      setError('Пожалуйста, заполните все обязательные поля')
      return
    }

    try {
      setLoading(true)
      setError(null)

      const bookingData: BookingCreate = {
        specialist_id: specialist!.id,
        date: date!,
        time: time!,
        name: name.trim(),
        phone: phone.trim(),
        additional_info: additionalInfo.trim() || undefined,
      }

      await api.post('/api/bookings', bookingData)
      
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
            onChange={(e) => setPhone(e.target.value)}
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
