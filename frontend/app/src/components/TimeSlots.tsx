import { useEffect, useState } from 'react'
import { useBookingStore } from '../store/bookingStore'
import api from '../api/client'
import type { Slot } from '../api/types'

export default function TimeSlots() {
  const { specialist, date, time, setTime, nextStep, prevStep } = useBookingStore()
  const [slots, setSlots] = useState<Slot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadSlots = async () => {
    if (!specialist || !date) return
    
    try {
      setLoading(true)
      const response = await api.get('/api/slots', {
        params: {
          specialist_id: specialist.id,
          date: date,
        },
      })
      setSlots(response.data.slots)
    } catch (err) {
      setError('Не удалось загрузить расписание')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!specialist || !date) {
      prevStep()
      return
    }
    loadSlots()
  }, [specialist, date])

  const handleSlotSelect = (slotTime: string) => {
    setTime(slotTime)
    nextStep()
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
          onClick={loadSlots}
          className="mt-2 text-blue-500 hover:text-blue-600"
        >
          Попробовать снова
        </button>
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-2 text-gray-900">
        Выберите время
      </h2>
      <p className="text-sm text-gray-600 mb-4">
        {new Date(date!).toLocaleDateString('ru-RU', {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        })}
      </p>

      {slots.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500">На эту дату нет свободных слотов</p>
          <button
            onClick={prevStep}
            className="mt-4 text-blue-500 hover:text-blue-600"
          >
            Вернуться к выбору даты
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-2">
          {slots.map((slot) => {
            const isSelected = time === slot.time
            
            return (
              <button
                key={slot.time}
                onClick={() => handleSlotSelect(slot.time)}
                className={`
                  slot-button
                  ${slot.available
                    ? isSelected
                      ? 'bg-blue-600 text-white font-bold'
                      : 'slot-available'
                    : 'slot-unavailable'
                  }
                `}
                disabled={!slot.available}
              >
                {slot.time}
              </button>
            )
          })}
        </div>
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
