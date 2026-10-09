export interface Specialist {
  id: number
  name: string
  specialization: string
}

export interface Slot {
  time: string
  slot_key: string
  available: boolean
}

export interface Availability {
  date: string
  has_slots: boolean
  slots_count: number
}

export interface BookingCreate {
  specialist_id: number
  date: string
  time: string
  name: string
  phone: string
  additional_info?: string
}

export interface BookingResponse {
  id: number
  specialist_name: string
  consultation_date: string
  consultation_time: string
  status: string
}
