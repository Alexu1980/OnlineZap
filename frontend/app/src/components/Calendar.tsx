import { useEffect, useState } from 'react'
import { useBookingStore } from '../store/bookingStore'
import api from '../api/client'
import type { Availability } from '../api/types'

export default function Calendar() {
  const { specialist, date: selectedDate, setDate, nextStep, prevStep } = useBookingStore()
  const [dates, setDates] = useState<Availability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadAvailableDates = async () => {
    if (!specialist) return
    
    try {
      setLoading(true)
      const response = await api.get('/availability', {
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

  useEffect(() => {
    if (!specialist) {
      prevStep()
      return
    }
    loadAvailableDates()
  }, [specialist])

  const handleDateSelect = (dateStr: string, isAvailable: boolean) => {
    if (!isAvailable) {
      console.log('Date not available:', dateStr)
      return
    }
    setDate(dateStr)
    nextStep()
  }

  const isWorkingDay = (dateStr: string) => {
    const date = new Date(dateStr)
    const dayIndex = date.getDay()
    // 0=Вс, 6=Сб - выходные
    return dayIndex >= 1 && dayIndex <= 5
  }

  const isDateAvailable = (dateStr: string) => {
    const availability = dates.find(d => d.date === dateStr)
    return availability?.has_slots || false
  }

  const getSlotsCount = (dateStr: string) => {
    const availability = dates.find(d => d.date === dateStr)
    return availability?.slots_count || 0
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

  // Генерируем календарную сетку
  const generateCalendarGrid = () => {
    if (dates.length === 0) return []

    const startDate = new Date(dates[0].date)
    const endDate = new Date(dates[dates.length - 1].date)
    
    // Находим начало недели (понедельник) для startDate
    const startDay = startDate.getDay()
    const adjustToMonday = startDay === 0 ? -6 : 1 - startDay
    const calendarStart = new Date(startDate)
    calendarStart.setDate(startDate.getDate() + adjustToMonday)
    
    // Находим конец недели (воскресенье) для endDate
    const endDay = endDate.getDay()
    const adjustToSunday = endDay === 0 ? 0 : 7 - endDay
    const calendarEnd = new Date(endDate)
    calendarEnd.setDate(endDate.getDate() + adjustToSunday)
    
    const grid: Date[] = []
    const current = new Date(calendarStart)
    
    while (current <= calendarEnd) {
      grid.push(new Date(current))
      current.setDate(current.getDate() + 1)
    }
    
    return grid
  }

  const calendarGrid = generateCalendarGrid()

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-gray-900">
        Выберите дату
      </h2>

      {/* Заголовки дней недели */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map((day) => (
          <div
            key={day}
            className="text-center text-xs font-medium text-gray-400 py-1"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Календарная сетка */}
      <div className="grid grid-cols-7 gap-1">
        {calendarGrid.map((date, index) => {
          const dateStr = date.toISOString().split('T')[0]
          const isAvailable = isDateAvailable(dateStr)
          const isWorking = isWorkingDay(dateStr)
          const isSelected = dateStr === selectedDate
          const slotsCount = getSlotsCount(dateStr)
          const isPast = dateStr < new Date().toISOString().split('T')[0]
          
          // Определяем стиль
          let buttonClass = 'p-2 rounded-lg text-center transition-all min-h-[44px] flex flex-col justify-center items-center'
          
          if (isPast || (!isWorking && !isAvailable)) {
            // Прошедшие и будущие выходные - серые, некликабельные
            buttonClass += ' bg-gray-100 text-gray-300 cursor-not-allowed'
          } else if (isWorking && isAvailable) {
            // Рабочие дни со слотами - синие
            buttonClass += isSelected 
              ? ' bg-blue-600 text-white font-bold'
              : ' bg-blue-500 text-white hover:bg-blue-600 cursor-pointer'
          } else if (isWorking && !isAvailable) {
            // Рабочие дни без слотов - темно-серые
            buttonClass += ' bg-gray-400 text-white cursor-not-allowed'
          } else {
            // Будущие выходные - светло-серые
            buttonClass += ' bg-gray-200 text-gray-400 cursor-not-allowed'
          }
          
          return (
            <button
              key={index}
              onClick={() => isWorking && isAvailable && handleDateSelect(dateStr, true)}
              style={!isWorking || !isAvailable || isPast ? { pointerEvents: 'none' } : {}}
              className={buttonClass}
              title={
                isPast 
                  ? 'Прошедшая дата' 
                  : !isWorking 
                    ? 'Выходной' 
                    : !isAvailable 
                      ? 'Нет свободных слотов' 
                      : `${slotsCount} слотов свободно`
              }
            >
              <div className="text-sm font-medium">{date.getDate()}</div>
            </button>
          )
        })}
      </div>

      {/* Легенда */}
      <div className="mt-6 flex flex-wrap gap-4 text-xs">
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
  )
}
