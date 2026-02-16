"""Pydantic schemas (API compatibility with existing frontend)."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import uuid


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    type: Literal["text", "plan_cards", "application_data"] = "text"
    content: str


class TransportationDetail(BaseModel):
    type: str
    departure_station: str
    arrival_station: str
    departure_time: str
    arrival_time: str
    price: int
    train_name: Optional[str] = None


class HotelDetail(BaseModel):
    name: str
    area: str
    price_per_night: int
    nights: int
    total_price: int
    rating: Optional[float] = None


class PlanSummary(BaseModel):
    depart_date: str
    return_date: str
    destination: str
    transportation: str
    hotel: str
    estimated_total: int
    policy_status: Literal["OK", "NG", "注意"]
    policy_note: Optional[str] = None


class TravelPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    summary: PlanSummary
    outbound_transportation: Optional[TransportationDetail] = None
    return_transportation: Optional[TransportationDetail] = None
    hotel: Optional[HotelDetail] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    user_id: str = "demo-user-1"
    company_name: Optional[str] = Field(None, description="将来のタグ付け等に備えて保持（本フェーズでは未使用）")


class ChatResponse(BaseModel):
    session_id: str
    messages: List[Message]
    plans: List[TravelPlan] = []


class ApplicationPayload(BaseModel):
    destination: str
    depart_date: str
    return_date: str
    purpose: str
    transportation: str
    transportation_cost: int
    hotel: str
    hotel_cost: int
    total_budget: int
    notes: str = ""


class PlanConfirmRequest(BaseModel):
    plan_id: str
    session_id: str
    user_id: str = "demo-user-1"
    purpose: Optional[str] = None


class PlanConfirmResponse(BaseModel):
    status: Literal["confirmed", "error"]
    application_payload: Optional[ApplicationPayload] = None
    error_message: Optional[str] = None


class TravelConditions(BaseModel):
    departure_location: Optional[str] = None
    destination: Optional[str] = None
    depart_date: Optional[str] = None
    return_date: Optional[str] = None
    budget: Optional[int] = None
    preferred_transportation: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None


class SessionData(BaseModel):
    session_id: str
    user_id: str
    conditions: TravelConditions = Field(default_factory=TravelConditions)
    plans: List[TravelPlan] = []
    messages: List[Message] = []
    created_at: str = ""
    updated_at: str = ""

