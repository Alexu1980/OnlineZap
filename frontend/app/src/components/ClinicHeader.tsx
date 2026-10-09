import { useEffect } from 'react'
import WebApp from '@twa-dev/sdk'
import { useBookingStore } from '../store/bookingStore'

export default function ClinicHeader() {
  const { step } = useBookingStore()

  useEffect(() => {
    if (step !== 'specialist') {
      WebApp.BackButton.show()
    } else {
      WebApp.BackButton.hide()
    }

    return () => {
      WebApp.BackButton.offClick(handleBack)
    }
  }, [step])

  const handleBack = () => {
    // Handle back button click
  }

  WebApp.BackButton.onClick(handleBack)

  return (
    <div className="bg-white p-4 shadow-sm flex items-center gap-3">
      {/* Логотип клиники */}
      <div className="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center">
        <svg
          className="w-8 h-8 text-white"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
          />
        </svg>
      </div>
      
      <div className="flex-1">
        <h1 className="text-lg font-bold text-gray-900">Клиника "Здоровье"</h1>
        <p className="text-sm text-gray-600">Запись на консультацию</p>
      </div>
    </div>
  )
}
