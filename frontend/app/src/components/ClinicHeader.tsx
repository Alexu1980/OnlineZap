import { useEffect } from 'react'
import WebApp from '@twa-dev/sdk'
import { useBookingStore } from '../store/bookingStore'

interface ClinicHeaderProps {
  showCabinet?: boolean
  onOpenCabinet?: () => void
  onCloseCabinet?: () => void
  onReset?: () => void
}

export default function ClinicHeader({ showCabinet = false, onOpenCabinet, onCloseCabinet, onReset }: ClinicHeaderProps) {
  const { step, prevStep } = useBookingStore()

  useEffect(() => {
    if (step !== 'specialist' && WebApp.BackButton && !showCabinet) {
      WebApp.BackButton.show()
      WebApp.BackButton.onClick(handleBack)
    } else {
      if (WebApp.BackButton) {
        WebApp.BackButton.hide()
      }
    }

    return () => {
      if (WebApp.BackButton) {
        WebApp.BackButton.offClick(handleBack)
      }
    }
  }, [step, showCabinet])

  const handleLogoClick = () => {
    // Сбрасываем состояние и возвращаемся на главный экран
    if (onReset) {
      onReset()
    }
  }

  const handleBack = () => {
    if (showCabinet && onCloseCabinet) {
      onCloseCabinet()
    } else {
      prevStep()
    }
  }

  const handleOpenCabinet = () => {
    if (onOpenCabinet) {
      onOpenCabinet()
    }
  }

  const showBackButton = step !== 'specialist' && !showCabinet

  return (
    <div className="bg-white p-4 shadow-sm flex items-center gap-3">
      {/* Кнопка "Назад" */}
      {showBackButton && (
        <button
          onClick={handleBack}
          className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors"
        >
          <svg
            className="w-5 h-5 text-gray-700"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
      )}
      
      {/* Логотип клиники */}
      <div 
        className="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center cursor-pointer hover:bg-blue-600 transition-colors"
        onClick={handleLogoClick}
        title="Вернуться на главный экран"
      >
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
      
      <div 
        className="flex-1 cursor-pointer"
        onClick={handleLogoClick}
        title="Вернуться на главный экран"
      >
        <h1 className="text-lg font-bold text-gray-900">Клиника "Здоровье"</h1>
        <p className="text-sm text-gray-600">Запись на консультацию</p>
      </div>
      
      {/* Кнопка "Личный кабинет" */}
      <button
        onClick={handleOpenCabinet}
        className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center hover:bg-blue-200 transition-colors"
        title="Личный кабинет"
      >
        <svg
          className="w-5 h-5 text-blue-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
          />
        </svg>
      </button>
    </div>
  )
}
