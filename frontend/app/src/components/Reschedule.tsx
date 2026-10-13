import { useEffect, useState } from 'react'
import { useBookingStore } from '../store/bookingStore'
import api, { getTelegramUserId } from '../api/client'
import WebApp from '@twa-dev/sdk'

interface Availability {
  date: string
  has_slots: boolean
  slots_count: number
}

interface Slot {
  time: string
  slot_key: string
  available: boolean
}

interface RescheduleProps {
  onClose?: () => void
  initialBookingId?: number
  initialSpecialistName?: string
  initialDate?: string
  initialTime?: string
}

export default function Reschedule({ onClose, initialBookingId, initialSpecialistName, initialDate, initialTime }: RescheduleProps) {
  const { date, time, setDate, setTime, prevStep, reset } = useBookingStore()
  const [availability, setAvailability] = useState<Availability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState<'calendar' | 'time' | 'confirm'>('calendar')
  const [slots, setSlots] = useState<Slot[]>([])
  const [bookingId, setBookingId] = useState<number | null>(initialBookingId || null)
  const [specialistName, setSpecialistName] = useState<string>(initialSpecialistName || '')
  const [oldDate, setOldDate] = useState<string>(initialDate || '')
  const [oldTime, setOldTime] = useState<string>(initialTime || '')
  const [rescheduling, setRescheduling] = useState(false)

  // Загружаем доступные даты
  const loadAvailability = async () => {
    if (!bookingId) return
    
    try {
      setLoading(true)
      const userId = getTelegramUserId()
      if (!userId) {
        setError('Не удалось получить данные пользователя')
        return
      }

      const response = await api.get(`/bookings/${bookingId}/available-slots`, {
        params: {
          user_telegram_id: userId,
          days: 30
        }
      })

      setAvailability(response.data.dates || [])
    } catch (err) {
      setError('Не удалось загрузить расписание')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Загружаем слоты для выбранной даты
  const loadSlots = async (dateStr: string) => {
    if (!bookingId || !specialistName) return
    
    try {
      setLoading(true)
      const userId = getTelegramUserId()
      if (!userId) return

      // Получаем specialist_id из booking
      const response = await api.get(`/bookings/${bookingId}/available-slots`, {
        params: {
          user_telegram_id: userId
        }
      })

      // Извлекаем specialist_id из ответа
      const specialistId = response.data?.specialist_id
      if (!specialistId) {
        setError('Не удалось получить данные специалиста')
        return
      }

      const slotsResponse = await api.get('/slots', {
        params: {
          specialist_id: specialistId,
          date: dateStr
        }
      })

      setSlots(slotsResponse.data.slots || [])
    } catch (err) {
      setError('Не удалось загрузить слоты')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initialBookingId) {
      setBookingId(initialBookingId)
      setSpecialistName(initialSpecialistName || '')
      setOldDate(initialDate || '')
      setOldTime(initialTime || '')
      loadAvailability()
    }
  }, [initialBookingId])

  useEffect(() => {
    WebApp.expand()
  }, [])

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      })
    } catch {
      return dateStr
    }
  }

  const handleDateSelect = (dateStr: string) => {
    setDate(dateStr)
    setCurrentStep('time')
    loadSlots(dateStr)
  }

  const handleTimeSelect = (time: string) => {
    setTime(time)
    setCurrentStep('confirm')
  }

  const handleConfirmReschedule = async () => {
    if (!bookingId || !date || !time) {
      setError('Отсутствуют данные для переноса')
      return
    }

    try {
      setRescheduling(true)
      const userId = getTelegramUserId()
      if (!userId) {
        setError('Не удалось получить данные пользователя')
        return
      }

      await api.post(`/bookings/${bookingId}/reschedule`, null, {
        params: {
          user_telegram_id: userId,
          new_date: date,
          new_time: time
        }
      })

      WebApp.HapticFeedback.notificationOccurred('success')
      window.alert(`✅ Консультация перенесена!\n\nНовая дата: ${formatDate(date)}\nВремя: ${time}`)
      
      reset()
      prevStep()
    } catch (err: any) {
      WebApp.HapticFeedback.notificationOccurred('error')
      setError(err.response?.data?.detail || 'Ошибка при переносе')
      console.error(err)
    } finally {
      setRescheduling(false)
    }
  }

  const handleBack = () => {
    if (currentStep === 'time') {
      setCurrentStep('calendar')
      setSlots([])
    } else if (currentStep === 'confirm') {
      setCurrentStep('time')
      setDate('')
    } else {
      prevStep()
    }
  }

  const isWorkingDay = (dateStr: string) => {
    const date = new Date(dateStr)
    const day = date.getDay()
    return day >= 1 && day <= 5
  }

  const isPastDate = (dateStr: string) => {
    return dateStr < new Date().toISOString().split('T')[0]
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
          onClick={() => window.location.reload()}
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
        🔄 Перенос консультации
      </h2>

      {/* Текущая запись */}
      {oldDate && oldTime && (
        <div className="card mb-4 bg-blue-50">
          <h3 className="font-medium text-gray-900 mb-2">Текущая запись:</h3>
          <div className="text-sm space-y-1">
            <p><span className="text-gray-600">Специалист:</span> {specialistName}</p>
            <p><span className="text-gray-600">Дата:</span> {formatDate(oldDate)}</p>
            <p><span className="text-gray-600">Время:</span> {oldTime}</p>
          </div>
        </div>
      )}

      {/* Календарь */}
      {currentStep === 'calendar' && (
        <div>
          <h3 className="text-base font-semibold mb-3 text-gray-900">Выберите новую дату</h3>
          
          <div className="grid grid-cols-7 gap-1 mb-2">
            {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day) => (
              <div key={day} className="text-center text-xs font-medium text-gray-400 py-1">
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {availability.slice(0, 35).map((avail, index) => {
              const date = new Date(avail.date)
              const isAvailable = avail.has_slots
              const isWorking = isWorkingDay(avail.date)
              const isPast = isPastDate(avail.date)
              
              let buttonClass = 'p-2 rounded-lg text-center transition-all min-h-[44px] flex flex-col justify-center items-center'
              
              if (isPast || (!isWorking && !isAvailable)) {
                buttonClass += ' bg-gray-100 text-gray-300 cursor-not-allowed'
              } else if (isWorking && isAvailable) {
                buttonClass += ' bg-blue-500 text-white hover:bg-blue-600 cursor-pointer'
              } else if (isWorking && !isAvailable) {
                buttonClass += ' bg-gray-400 text-white cursor-not-allowed'
              } else {
                buttonClass += ' bg-gray-200 text-gray-400 cursor-not-allowed'
              }
              
              return (
                <button
                  key={index}
                  onClick={() => isWorking && isAvailable && !isPast && handleDateSelect(avail.date)}
                  disabled={!isWorking || !isAvailable || isPast}
                  className={buttonClass}
                  title={
                    isPast 
                      ? 'Прошедшая дата' 
                      : !isWorking 
                        ? 'Выходной' 
                        : !isAvailable 
                          ? 'Нет свободных слотов' 
                          : `${avail.slots_count} слотов свободно`
                  }
                >
                  <div className="text-sm font-medium">{date.getDate()}</div>
                </button>
              )
            })}
          </div>

          <div className="mt-4 flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-blue-500"></div>
              <span className="text-gray-600">Свободно</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-gray-400"></div>
              <span className="text-gray-600">Занято</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-gray-200"></div>
              <span className="text-gray-600">Выходной</span>
            </div>
          </div>
        </div>
      )}

      {/* Выбор времени */}
      {currentStep === 'time' && (
        <div>
          <h3 className="text-base font-semibold mb-2 text-gray-900">Выберите время</h3>
          <p className="text-sm text-gray-600 mb-4">
            {formatDate(date)}
          </p>

          {slots.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">На эту дату нет свободных слотов</p>
              <button
                onClick={() => setCurrentStep('calendar')}
                className="mt-4 text-blue-500 hover:text-blue-600"
              >
                Вернуться к выбору даты
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {slots.map((slot) => (
                <button
                  key={slot.time}
                  onClick={() => handleTimeSelect(slot.time)}
                  className={`
                    slot-button
                    ${slot.available
                      ? 'slot-available hover:bg-blue-600 hover:text-white'
                      : 'slot-unavailable'
                    }
                  `}
                  disabled={!slot.available}
                >
                  {slot.time}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Подтверждение */}
      {currentStep === 'confirm' && (
        <div>
          <h3 className="text-base font-semibold mb-4 text-gray-900">Подтвердите перенос</h3>
          
          <div className="card bg-green-50 mb-4">
            <h4 className="font-medium text-gray-900 mb-2">Новая запись:</h4>
            <div className="text-sm space-y-1">
              <p><span className="text-gray-600">Специалист:</span> {specialistName}</p>
              <p><span className="text-gray-600">Дата:</span> {formatDate(date)}</p>
              <p><span className="text-gray-600">Время:</span> {time}</p>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleBack}
              className="btn-secondary flex-1"
            >
              Назад
            </button>
            <button
              onClick={handleConfirmReschedule}
              disabled={rescheduling}
              className="btn-primary flex-1 disabled:opacity-50"
            >
              {rescheduling ? 'Перенос...' : 'Перенести'}
            </button>
          </div>
        </div>
      )}

      {/* Кнопка назад */}
      <div className="mt-4 flex gap-2">
        <button
          onClick={handleBack}
          className="text-blue-600 hover:text-blue-700 text-sm"
        >
          ← Назад
        </button>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-700 text-sm"
          >
            Закрыть
          </button>
        )}
      </div>
    </div>
  )
}
