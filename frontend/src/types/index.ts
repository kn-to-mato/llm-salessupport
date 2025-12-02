// API Types

export interface Message {
  role: 'user' | 'assistant' | 'system';
  type: 'text' | 'plan_cards' | 'application_data';
  content: string;
}

export interface TransportationDetail {
  type: string;
  departure_station: string;
  arrival_station: string;
  departure_time: string;
  arrival_time: string;
  price: number;
  train_name?: string;
}

export interface HotelDetail {
  name: string;
  area: string;
  price_per_night: number;
  nights: number;
  total_price: number;
  rating?: number;
}

export interface PlanSummary {
  depart_date: string;
  return_date: string;
  destination: string;
  transportation: string;
  hotel: string;
  estimated_total: number;
  policy_status: 'OK' | 'NG' | '注意';
  policy_note?: string;
}

export interface TravelPlan {
  plan_id: string;
  label: string;
  summary: PlanSummary;
  outbound_transportation?: TransportationDetail;
  return_transportation?: TransportationDetail;
  hotel?: HotelDetail;
}

export interface ChatRequest {
  session_id?: string;
  message: string;
  user_id: string;
}

export interface ChatResponse {
  session_id: string;
  messages: Message[];
  plans: TravelPlan[];
}

export interface ApplicationPayload {
  destination: string;
  depart_date: string;
  return_date: string;
  purpose: string;
  transportation: string;
  transportation_cost: number;
  hotel: string;
  hotel_cost: number;
  total_budget: number;
  notes: string;
}

export interface PlanConfirmRequest {
  plan_id: string;
  session_id: string;
  user_id: string;
  purpose?: string;
}

export interface PlanConfirmResponse {
  status: 'confirmed' | 'error';
  application_payload?: ApplicationPayload;
  error_message?: string;
}

// UI State Types
export interface ChatMessage extends Message {
  id: string;
  timestamp: Date;
  plans?: TravelPlan[];
  applicationData?: ApplicationPayload;
}
