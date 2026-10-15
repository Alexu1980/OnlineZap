import { useEffect, useState } from 'react'
import WebApp from '@twa-dev/sdk'
import ClinicHeader from './components/ClinicHeader'
import SpecialistSelect from './components/SpecialistSelect'
import Calendar from './components/Calendar'
import TimeSlots from './components/TimeSlots'
import ContactForm from './components/ContactForm'
import Confirmation from './components/Confirmation'
import PersonalCabinet from './components/PersonalCabinet'
import Reschedule from './components/Reschedule'
import { useBookingStore } from './store/bookingStore'

function App() {
  const { step, reset } = useBookingStore()
  const [showCabinet, setShowCabinet] = useState(false)
  const [showReschedule, setShowReschedule] = useState(false)
  const [rescheduleData, setRescheduleData] = useState<{ id: number; name: string; date: string; time: string } | null>(null)

  const handleReset = () => {
    reset()
    setShowCabinet(false)
    setShowReschedule(false)
    setRescheduleData(null)
  }

  useEffect(() => {
    // Инициализация Telegram WebApp
    WebApp.ready()
    WebApp.expand()
    
    // Настройка цветов темы
    WebApp.setHeaderColor('#FFFFFF')
    WebApp.setBackgroundColor('#FFFFFF')
  }, [])

  const renderStep = () => {
    switch (step) {
      case 'specialist':
        return <SpecialistSelect />
      case 'calendar':
        return <Calendar />
      case 'slots':
        return <TimeSlots />
      case 'form':
        return <ContactForm />
      case 'confirmation':
        return <Confirmation />
      default:
        return <SpecialistSelect />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <ClinicHeader 
        showCabinet={showCabinet}
        onOpenCabinet={() => setShowCabinet(true)}
        onCloseCabinet={() => setShowCabinet(false)}
        onReset={handleReset}
      />
      <main className="p-4">
        {showReschedule && rescheduleData ? (
          <Reschedule 
            onClose={() => {
              setShowReschedule(false)
              setRescheduleData(null)
            }}
            initialBookingId={rescheduleData.id}
            initialSpecialistName={rescheduleData.name}
            initialDate={rescheduleData.date}
            initialTime={rescheduleData.time}
          />
        ) : showCabinet ? (
          <PersonalCabinet 
            onClose={() => setShowCabinet(false)}
            onOpenReschedule={(id, name, date, time) => {
              setShowCabinet(false)
              setRescheduleData({ id, name, date, time })
              setShowReschedule(true)
            }}
          />
        ) : (
          renderStep()
        )}
      </main>
    </div>
  )
}

export default App
