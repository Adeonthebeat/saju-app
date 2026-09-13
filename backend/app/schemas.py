from datetime import date, datetime, time
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Gender(str, Enum):
    male = "male"
    female = "female"


class Calendar(str, Enum):
    solar = "solar"
    lunar = "lunar"


class SajuAnalyzeRequest(BaseModel):
    # 앱인토스 SDK User.getAnonymousKey()가 발급하는 앱-사용자 단위 익명 해시.
    # 없으면(발급 실패/구버전 앱) 조회 이력 없이 1회성으로만 분석한다.
    user_key: Optional[str] = None
    birth_date: date
    birth_time: Optional[time] = None
    is_time_unknown: bool = False
    calendar: Calendar = Calendar.solar
    is_lunar_leap_month: bool = False
    gender: Gender


class SajuAnalysisResult(BaseModel):
    """Gemini가 채우는 6가지 분석 결과. response_schema로도 그대로 재사용한다."""

    career_fit: str  # 1) 타고난 직업·적성 (그릇 진단)
    career_timing: str  # 2) 타이밍과 이동수 (운의 흐름)
    side_business: str  # 3) 사주 기반 부업·N잡
    wealth_building: str  # 4) 재물운과 자산 증식법
    work_relationships: str  # 5) 일복과 직장 인간관계
    luck_improvement: str  # 6) 직업 개운법


class PillarsView(BaseModel):
    year: str
    month: str
    day: str
    hour: Optional[str] = None


class SajuAnalyzeResponse(BaseModel):
    profile_id: UUID
    chart_id: UUID
    pillars: PillarsView
    five_elements: dict[str, int]
    analysis: SajuAnalysisResult
    cached: bool


class SajuHistoryItem(SajuAnalyzeResponse):
    created_at: datetime  # 이 조회 이벤트(saju_profiles)가 기록된 시각
