import { useEffect, useState } from 'react'
import { useBookingStore } from '../store/bookingStore'
import api from '../api/client'
import type { Availability } from '../api/types'

export default function Calendar() {
  const { specialist, date, setDate, nextStep, prevStep } = useBookingStore()
  const [dates, setDates] = useState<Availability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!specialist) {
      prevStep()
      return
    }
    loadAvailableDates()
  }, [specialist])

  const loadAvailableDates = async () => {
    try {
      setLoading(true)
      const response = await api.get('/api/availability', {
        params: {
          specialist_id: specialist.id,
          days: 30,
        },
      })
      setDates(response.data.dates)
    } catch (err) {
      setError('Не удалось загрузить расписание')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDateSelect = (dateStr: string) => {
    setDate(dateStr)
    nextStep()
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.getDate()
  }

  const getDayName = (dateStr: string) => {
    const date = new Date(dateStr)
    const days = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    return days[date.getDay()]
  }

  const getMonthName = (dateStr: string) => {
    const date = new Date(dateStr)
    const months = [
      'Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
      'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'
    ]
    return months[date.getMonth()]
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center text-red-500 py-4">
        <p>{error}</p>
        <button
          onClick={loadAvailableDates}
          className="mt-2 text-blue-500 hover:text-blue-600"
        >
          Попробовать снова
        </button>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-gray-900">
        Выберите дату
      </h2>

      <div className="grid grid-cols-7 gap-2 mb-4">
        {/* Заголовки дней недели */}
        {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day) => (
          <div
            key={day}
            className="calendar-day text-center text-sm font-medium text-gray-500"
          >
            {day}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-2">
        {dates.map((item) => {
          const isSelected = date === item.date
          const isAvailable = item.has_slots
          
          return (
            <button
              key={item.date}
              onClick={() => isAvailable && handleDateSelect(item.date)}
              className={`
                calendar-day
                ${isAvailable
                  ? isSelected
                    ? 'bg-blue-600 text-white font-bold'
                    : 'calendar-day-available'
                  : 'calendar-day-unavailable'
                }
              `}
              disabled={!isAvailable}
              title={isAvailable ? `${item.slots_count} слотов свободно` : 'Нет свободных слотов'}
            >
              <div className="text-sm">{formatDate(item.date)}</div>
              <div className="text-xs opacity-75">{getDayName(item.date)}</div>
            </button>
          )
        })}
      </div>

      {dates.length === 0 && (
        <p className="text-center text-gray-500 py-4">
          Нет доступных дат для выбранного специалиста
        </p>
      )}

      {/* Легенда */}
      <div className="mt-6 flex justify-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-blue-500"></div>
          <span className="text-gray-600">Свободно</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded bg-gray-300"></div>
          <span className="text-gray-600">Занято</span>
        </div>
      </div>
    </div>
  )
}
