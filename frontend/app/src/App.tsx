import { useEffect, useState } from 'react'
import WebApp from '@twa-dev/sdk'
import ClinicHeader from './components/ClinicHeader'
import SpecialistSelect from './components/SpecialistSelect'
import Calendar from './components/Calendar'
import TimeSlots from './components/TimeSlots'
import ContactForm from './components/ContactForm'
import Confirmation from './components/Confirmation'
import PersonalCabinet from './components/PersonalCabinet'
import { useBookingStore } from './store/bookingStore'

function App() {
  const { step } = useBookingStore()
  const [showCabinet, setShowCabinet] = useState(false)

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
      />
      <main className="p-4">
        {showCabinet ? (
          <PersonalCabinet onClose={() => setShowCabinet(false)} />
        ) : (
          renderStep()
        )}
      </main>
    </div>
  )
}

export default App
