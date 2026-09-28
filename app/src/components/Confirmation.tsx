import { useEffect } from 'react'
import { WebApp } from '@twa-dev/sdk'
import { useBookingStore } from '../store/bookingStore'

export default function Confirmation() {
  const { reset } = useBookingStore()

  useEffect(() => {
    // Показываем успешное сообщение в Telegram WebApp
    WebApp.HapticFeedback.notificationOccurred('success')
    
    // Показываем стандартное окно завершения
    WebApp.MainButton.setText("Завершить")
    WebApp.MainButton.show()
    
    WebApp.MainButton.onClick(() => {
      reset()
      WebApp.close()
    })
  }, [])

  return (
    <div className="text-center py-8">
      {/* Иконка успеха */}
      <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
        <svg
          className="w-8 h-8 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </div>

      <h2 className="text-xl font-bold text-gray-900 mb-2">
        Запись создана!
      </h2>
      
      <p className="text-gray-600 mb-6">
        Ваша запись на консультацию успешно создана. Мы отправим вам напоминание заранее.
      </p>

      <div className="card bg-gray-50 text-left">
        <h3 className="font-medium text-gray-900 mb-2">Что дальше?</h3>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Мы отправим вам напоминание за 24 часа до консультации</li>
          <li>• Пожалуйста, будьте готовы за 5 минут до назначенного времени</li>
          <li>• Для отмены или переноса свяжитесь с менеджером</li>
        </ul>
      </div>
    </div>
  )
}
