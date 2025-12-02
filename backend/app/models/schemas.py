"""Pydanticスキーマ定義"""
from datetime import date
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import uuid


class Message(BaseModel):
    """チャットメッセージ"""
    role: Literal["user", "assistant", "system"]
    type: Literal["text", "plan_cards", "application_data"] = "text"
    content: str


class TransportationDetail(BaseModel):
    """交通手段の詳細"""
    type: str = Field(..., description="交通手段タイプ（新幹線、飛行機等）")
    departure_station: str = Field(..., description="出発駅/空港")
    arrival_station: str = Field(..., description="到着駅/空港")
    departure_time: str = Field(..., description="出発時刻")
    arrival_time: str = Field(..., description="到着時刻")
    price: int = Field(..., description="片道料金")
    train_name: Optional[str] = Field(None, description="列車名/便名")


class HotelDetail(BaseModel):
    """宿泊先の詳細"""
    name: str = Field(..., description="ホテル名")
    area: str = Field(..., description="エリア")
    price_per_night: int = Field(..., description="1泊あたりの料金")
    nights: int = Field(..., description="宿泊数")
    total_price: int = Field(..., description="宿泊合計料金")
    rating: Optional[float] = Field(None, description="評価")


class PlanSummary(BaseModel):
    """プランサマリー"""
    depart_date: str = Field(..., description="出発日")
    return_date: str = Field(..., description="帰着日")
    destination: str = Field(..., description="目的地")
    transportation: str = Field(..., description="交通手段概要")
    hotel: str = Field(..., description="宿泊先概要")
    estimated_total: int = Field(..., description="概算総額")
    policy_status: Literal["OK", "NG", "注意"] = Field(..., description="規程評価")
    policy_note: Optional[str] = Field(None, description="規程に関する備考")


class TravelPlan(BaseModel):
    """出張プラン"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str = Field(..., description="プランラベル（プランA等）")
    summary: PlanSummary
    outbound_transportation: Optional[TransportationDetail] = None
    return_transportation: Optional[TransportationDetail] = None
    hotel: Optional[HotelDetail] = None


class ChatRequest(BaseModel):
    """チャットリクエスト"""
    session_id: Optional[str] = None
    message: str
    user_id: str = "demo-user-1"


class ChatResponse(BaseModel):
    """チャットレスポンス"""
    session_id: str
    messages: List[Message]
    plans: List[TravelPlan] = []


class ApplicationPayload(BaseModel):
    """申請データペイロード"""
    destination: str = Field(..., description="目的地")
    depart_date: str = Field(..., description="出発日")
    return_date: str = Field(..., description="帰着日")
    purpose: str = Field(..., description="出張目的")
    transportation: str = Field(..., description="交通手段")
    transportation_cost: int = Field(..., description="交通費")
    hotel: str = Field(..., description="宿泊先")
    hotel_cost: int = Field(..., description="宿泊費")
    total_budget: int = Field(..., description="合計予算")
    notes: str = Field("", description="備考")


class PlanConfirmRequest(BaseModel):
    """プラン確定リクエスト"""
    plan_id: str
    session_id: str
    user_id: str = "demo-user-1"
    purpose: Optional[str] = Field(None, description="出張目的（追加情報）")


class PlanConfirmResponse(BaseModel):
    """プラン確定レスポンス"""
    status: Literal["confirmed", "error"]
    application_payload: Optional[ApplicationPayload] = None
    error_message: Optional[str] = None


# セッション関連
class TravelConditions(BaseModel):
    """出張条件"""
    departure_location: Optional[str] = Field(None, description="出発地")
    destination: Optional[str] = Field(None, description="目的地")
    depart_date: Optional[str] = Field(None, description="出発日")
    return_date: Optional[str] = Field(None, description="帰着日")
    budget: Optional[int] = Field(None, description="予算上限")
    preferred_transportation: Optional[str] = Field(None, description="希望交通手段")
    purpose: Optional[str] = Field(None, description="出張目的")
    notes: Optional[str] = Field(None, description="その他要望")


class SessionData(BaseModel):
    """セッションデータ"""
    session_id: str
    user_id: str
    conditions: TravelConditions = Field(default_factory=TravelConditions)
    plans: List[TravelPlan] = []
    messages: List[Message] = []
    created_at: str = ""
    updated_at: str = ""
