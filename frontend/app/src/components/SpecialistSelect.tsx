import { useEffect, useState } from 'react'
import { useBookingStore } from '../store/bookingStore'
import api from '../api/client'
import type { Specialist } from '../api/types'

export default function SpecialistSelect() {
  const { setSpecialist, nextStep } = useBookingStore()
  const [specialists, setSpecialists] = useState<Specialist[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadSpecialists()
  }, [])

  const loadSpecialists = async () => {
    try {
      setLoading(true)
      const response = await api.get('/specialists')
      setSpecialists(response.data.specialists)
    } catch (err) {
      setError('Не удалось загрузить список специалистов')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (spec: Specialist) => {
    setSpecialist(spec)
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
          onClick={loadSpecialists}
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
        Выберите специалиста
      </h2>
      
      <div className="space-y-2">
        {specialists.map((spec) => (
          <button
            key={spec.id}
            onClick={() => handleSelect(spec)}
            className="w-full card text-left hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                <span className="text-blue-600 font-semibold">
                  {spec.name.charAt(0)}
                </span>
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">{spec.name}</h3>
                <p className="text-sm text-gray-600">{spec.specialization}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
      
      {specialists.length === 0 && (
        <p className="text-center text-gray-500 py-4">
          Специалисты временно недоступны
        </p>
      )}
    </div>
  )
}
