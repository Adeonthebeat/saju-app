from fastapi import APIRouter, HTTPException

from .. import repository
from ..saju_calculator import SajuCalculationError, calculate_pillars
from ..schemas import (
    PillarsView,
    SajuAnalysisResult,
    SajuAnalyzeRequest,
    SajuAnalyzeResponse,
    SajuHistoryItem,
)

router = APIRouter(prefix="/api/saju", tags=["saju"])


@router.post("/analyze", response_model=SajuAnalyzeResponse)
def analyze(payload: SajuAnalyzeRequest) -> SajuAnalyzeResponse:
    try:
        pillars = calculate_pillars(
            birth_date=payload.birth_date,
            birth_time=payload.birth_time,
            is_time_unknown=payload.is_time_unknown,
            calendar=payload.calendar.value,
            gender=payload.gender.value,
            is_lunar_leap_month=payload.is_lunar_leap_month,
        )
    except SajuCalculationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chart, analysis_row, cached = repository.get_or_create_analysis(
        payload.gender.value, pillars
    )
    profile = repository.record_profile(
        user_key=payload.user_key,
        birth_date=payload.birth_date,
        birth_time=payload.birth_time,
        is_time_unknown=payload.is_time_unknown,
        calendar=payload.calendar.value,
        gender=payload.gender.value,
        chart_id=chart["id"],
    )

    return SajuAnalyzeResponse(
        profile_id=profile["id"],
        chart_id=chart["id"],
        pillars=PillarsView(
            year=pillars.year_pillar,
            month=pillars.month_pillar,
            day=pillars.day_pillar,
            hour=pillars.hour_pillar,
        ),
        five_elements=pillars.five_elements,
        analysis=SajuAnalysisResult(
            career_fit=analysis_row["career_fit"],
            career_timing=analysis_row["career_timing"],
            side_business=analysis_row["side_business"],
            wealth_building=analysis_row["wealth_building"],
            work_relationships=analysis_row["work_relationships"],
            luck_improvement=analysis_row["luck_improvement"],
        ),
        cached=cached,
    )


@router.get("/history", response_model=list[SajuHistoryItem])
def history(user_key: str) -> list[dict]:
    return repository.get_user_history(user_key)
