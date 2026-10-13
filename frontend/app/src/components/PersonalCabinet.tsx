import { useEffect, useState } from 'react'
import api, { getTelegramUserId } from '../api/client'
import WebApp from '@twa-dev/sdk'

interface Booking {
  id: number
  specialist_name: string
  consultation_date: string
  consultation_time: string
  status: string
  created_at?: string
}

interface PersonalCabinetProps {
  onClose?: () => void
  onOpenReschedule?: (bookingId: number, specialistName: string, date: string, time: string) => void
}

export default function PersonalCabinet({ onClose, onOpenReschedule }: PersonalCabinetProps) {
  const [activeBookings, setActiveBookings] = useState<Booking[]>([])
  const [pastBookings, setPastBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showHistory, setShowHistory] = useState(false)
  const [cancellingId, setCancellingId] = useState<number | null>(null)

  const handleCancelBooking = async (bookingId: number) => {
    if (!window.confirm('Вы уверены, что хотите отменить запись?')) {
      return
    }

    try {
      setCancellingId(bookingId)
      const userId = getTelegramUserId()
      if (!userId) {
        setError('Не удалось получить данные пользователя')
        return
      }

      await api.post(`/bookings/${bookingId}/cancel`, null, {
        params: { user_telegram_id: userId }
      })

      // Обновляем список записей
      await loadBookings()
      WebApp.HapticFeedback.notificationOccurred('success')
    } catch (err: any) {
      WebApp.HapticFeedback.notificationOccurred('error')
      setError(err.response?.data?.detail || 'Ошибка при отмене записи')
      console.error(err)
    } finally {
      setCancellingId(null)
    }
  }

  const handleRescheduleBooking = (bookingId: number) => {
    // Находим booking в activeBookings
    const booking = activeBookings.find(b => b.id === bookingId)
    if (booking && onOpenReschedule) {
      onOpenReschedule(bookingId, booking.specialist_name, booking.consultation_date, booking.consultation_time)
    }
  }

  const loadBookings = async () => {
    try {
      setLoading(true)
      const userId = getTelegramUserId()
      if (!userId) {
        setError('Не удалось получить данные пользователя')
        return
      }

      const response = await api.get('/user/bookings', {
        params: {
          user_telegram_id: userId,
          show_history: showHistory
        }
      })

      setActiveBookings(response.data.active_bookings || [])
      setPastBookings(response.data.past_bookings || [])
    } catch (err) {
      setError('Не удалось загрузить записи')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBookings()
  }, [showHistory])

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

  const getStatusIcon = (status: string) => {
    const icons: Record<string, string> = {
      'Подтверждена': '✅',
      'Отменена': '❌',
      'Завершена': '✔️',
      'Ожидает': '⏳',
      'Перенесена': '🔄'
    }
    return icons[status] || '📌'
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'Подтверждена': 'text-green-600',
      'Отменена': 'text-red-600',
      'Завершена': 'text-gray-600',
      'Ожидает': 'text-yellow-600',
      'Перенесена': 'text-blue-600'
    }
    return colors[status] || 'text-gray-600'
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
          onClick={loadBookings}
          className="mt-2 text-blue-500 hover:text-blue-600"
        >
          Попробовать снова
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          📋 Мои записи
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            ← Назад
          </button>
        )}
      </div>

      {/* Активные записи */}
      {activeBookings.length > 0 ? (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-700">Активные записи</h3>
          </div>
          <div className="space-y-3">
            {activeBookings.map((booking) => (
              <div key={booking.id} className="card bg-white border border-gray-200">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">
                      {booking.specialist_name}
                    </h4>
                    <p className="text-sm text-gray-600 mt-1">
                      📅 {formatDate(booking.consultation_date)}
                    </p>
                    <p className="text-sm text-gray-600">
                      🕐 {booking.consultation_time}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-medium ${getStatusColor(booking.status)}`}>
                      {getStatusIcon(booking.status)} {booking.status}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-gray-500 pt-2 border-t border-gray-100 flex items-center justify-between">
                  <span>Запись #{booking.id}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleRescheduleBooking(booking.id)}
                      className="text-blue-600 hover:text-blue-700 text-xs px-2 py-1 bg-blue-50 rounded"
                    >
                      🔄 Перенести
                    </button>
                    <button
                      onClick={() => handleCancelBooking(booking.id)}
                      disabled={cancellingId === booking.id}
                      className="text-red-600 hover:text-red-700 text-xs px-2 py-1 bg-red-50 rounded disabled:opacity-50"
                    >
                      {cancellingId === booking.id ? 'От��ена...' : '❌ Отменить'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="mb-6 text-center py-8 bg-gray-50 rounded-lg">
          <p className="text-gray-500">У вас пока нет активных записей</p>
        </div>
      )}

      {/* Прошлые записи */}
      {pastBookings.length > 0 && (
        <div>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <span className="text-sm font-medium text-gray-700">
              📜 История ({pastBookings.length} записей)
            </span>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${showHistory ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {showHistory && (
            <div className="mt-3 space-y-3">
              {pastBookings.map((booking) => (
                <div key={booking.id} className="card bg-white border border-gray-200 opacity-75">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900">
                        {booking.specialist_name}
                      </h4>
                      <p className="text-sm text-gray-600 mt-1">
                        📅 {formatDate(booking.consultation_date)}
                      </p>
                      <p className="text-sm text-gray-600">
                        🕐 {booking.consultation_time}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs font-medium ${getStatusColor(booking.status)}`}>
                        {getStatusIcon(booking.status)} {booking.status}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 pt-2 border-t border-gray-100">
                    Запись #{booking.id}
                    {booking.created_at && ` • Создана: ${booking.created_at}`}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
