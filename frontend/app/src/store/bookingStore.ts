import { create } from 'zustand'

export type Step = 'specialist' | 'calendar' | 'slots' | 'form' | 'confirmation'

interface Specialist {
  id: number
  name: string
  specialization: string
}

interface BookingState {
  // Данные
  specialist: Specialist | null
  date: string
  time: string
  step: Step
  
  // Действия
  setSpecialist: (specialist: Specialist) => void
  setDate: (date: string) => void
  setTime: (time: string) => void
  setStep: (step: Step) => void
  nextStep: () => void
  prevStep: () => void
  reset: () => void
}

export const useBookingStore = create<BookingState>((set) => ({
  specialist: null,
  date: '',
  time: '',
  step: 'specialist',
  
  setSpecialist: (specialist) => set({ specialist }),
  setDate: (date) => set({ date }),
  setTime: (time) => set({ time }),
  setStep: (step) => set({ step }),
  
  nextStep: () => set((state) => {
    const steps: Step[] = ['specialist', 'calendar', 'slots', 'form', 'confirmation']
    const currentIndex = steps.indexOf(state.step)
    if (currentIndex < steps.length - 1) {
      return { step: steps[currentIndex + 1] }
    }
    return state
  }),
  
  prevStep: () => set((state) => {
    const steps: Step[] = ['specialist', 'calendar', 'slots', 'form', 'confirmation']
    const currentIndex = steps.indexOf(state.step)
    if (currentIndex > 0) {
      return { step: steps[currentIndex - 1] }
    }
    return state
  }),
  
  reset: () => set({
    specialist: null,
    date: '',
    time: '',
    step: 'specialist',
  }),
}))
