from __future__ import annotations

from datetime import date, time
from typing import Optional

from postgrest.exceptions import APIError

from . import gemini_client
from .saju_calculator import PillarResult
from .supabase_client import get_supabase

UNIQUE_VIOLATION = "23505"


def _find_chart(gender: str, pillars: PillarResult) -> Optional[dict]:
    sb = get_supabase()
    query = (
        sb.table("saju_charts")
        .select("*")
        .eq("gender", gender)
        .eq("year_pillar", pillars.year_pillar)
        .eq("month_pillar", pillars.month_pillar)
        .eq("day_pillar", pillars.day_pillar)
    )
    query = (
        query.is_("hour_pillar", "null")
        if pillars.hour_pillar is None
        else query.eq("hour_pillar", pillars.hour_pillar)
    )
    result = query.limit(1).execute()
    return result.data[0] if result.data else None


def _get_or_create_chart(gender: str, pillars: PillarResult) -> dict:
    existing = _find_chart(gender, pillars)
    if existing is not None:
        return existing

    sb = get_supabase()
    row = {
        "gender": gender,
        "year_pillar": pillars.year_pillar,
        "month_pillar": pillars.month_pillar,
        "day_pillar": pillars.day_pillar,
        "hour_pillar": pillars.hour_pillar,
        "is_time_unknown": pillars.hour_pillar is None,
        "five_elements": pillars.five_elements,
    }
    try:
        result = sb.table("saju_charts").insert(row).execute()
        return result.data[0]
    except APIError as exc:
        if exc.code != UNIQUE_VIOLATION:
            raise
        # 동시 요청이 같은 팔자 조합을 먼저 만들었을 경우 그걸 그대로 재사용한다.
        existing = _find_chart(gender, pillars)
        if existing is None:
            raise
        return existing


def _find_completed_analysis(chart_id: str) -> Optional[dict]:
    sb = get_supabase()
    result = (
        sb.table("saju_analyses")
        .select("*")
        .eq("saju_chart_id", chart_id)
        .eq("status", "completed")
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _create_analysis(chart_id: str, gender: str, pillars: PillarResult) -> dict:
    from .config import get_settings

    settings = get_settings()
    sb = get_supabase()

    try:
        gemini_result = gemini_client.analyze_saju(gender=gender, pillars=pillars)
    except Exception as exc:
        sb.table("saju_analyses").insert(
            {
                "saju_chart_id": chart_id,
                "status": "failed",
                "error_message": str(exc),
                "gemini_model": settings.gemini_model,
            }
        ).execute()
        raise

    row = {
        "saju_chart_id": chart_id,
        "status": "completed",
        "career_fit": gemini_result.career_fit,
        "career_timing": gemini_result.career_timing,
        "side_business": gemini_result.side_business,
        "wealth_building": gemini_result.wealth_building,
        "work_relationships": gemini_result.work_relationships,
        "luck_improvement": gemini_result.luck_improvement,
        "gemini_model": settings.gemini_model,
    }
    try:
        result = sb.table("saju_analyses").insert(row).execute()
        return result.data[0]
    except APIError as exc:
        if exc.code != UNIQUE_VIOLATION:
            raise
        # 동시 요청이 이미 이 팔자 조합을 분석해 저장했다면 그 결과를 재사용한다
        # (Gemini는 이미 호출했지만, DB에는 먼저 도착한 결과만 남긴다).
        existing = _find_completed_analysis(chart_id)
        if existing is None:
            raise
        return existing


def get_or_create_analysis(gender: str, pillars: PillarResult) -> tuple[dict, dict, bool]:
    """팔자 조합 캐시를 확인하고, 없으면 Gemini를 호출해 1회만 생성한다.

    반환값: (saju_charts 행, saju_analyses 행, 캐시에서 재사용했는지 여부)
    """
    chart = _get_or_create_chart(gender, pillars)

    cached_analysis = _find_completed_analysis(chart["id"])
    if cached_analysis is not None:
        return chart, cached_analysis, True

    analysis = _create_analysis(chart["id"], gender, pillars)
    return chart, analysis, False


def record_profile(
    *,
    user_key: Optional[str],
    birth_date: date,
    birth_time: Optional[time],
    is_time_unknown: bool,
    calendar: str,
    gender: str,
    chart_id: str,
) -> dict:
    sb = get_supabase()
    row = {
        "user_key": user_key,
        "birth_date": birth_date.isoformat(),
        "birth_time": birth_time.isoformat() if birth_time else None,
        "is_time_unknown": is_time_unknown,
        "calendar": calendar,
        "gender": gender,
        "saju_chart_id": chart_id,
    }
    result = sb.table("saju_profiles").insert(row).execute()
    return result.data[0]


def get_user_history(user_key: str) -> list[dict]:
    """user_key로 조회한 이력을 profile_id/chart_id/pillars/analysis 형태로
    재구성해서 반환한다 — Supabase의 중첩 join 형태를 라우터가 몰라도 되게 한다.
    분석이 아직 없는(실패/진행중) 조합은 목록에서 제외한다.
    """
    sb = get_supabase()
    result = (
        sb.table("saju_profiles")
        .select("id, created_at, saju_charts(id, year_pillar, month_pillar, day_pillar, hour_pillar, five_elements, saju_analyses(*))")
        .eq("user_key", user_key)
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for profile in result.data:
        chart = profile.get("saju_charts")
        if not chart:
            continue
        analyses = [a for a in chart.get("saju_analyses", []) if a.get("status") == "completed"]
        if not analyses:
            continue
        analysis = analyses[0]

        items.append(
            {
                "profile_id": profile["id"],
                "chart_id": chart["id"],
                "created_at": profile["created_at"],
                "pillars": {
                    "year": chart["year_pillar"],
                    "month": chart["month_pillar"],
                    "day": chart["day_pillar"],
                    "hour": chart["hour_pillar"],
                },
                "five_elements": chart["five_elements"],
                "analysis": {
                    "career_fit": analysis["career_fit"],
                    "career_timing": analysis["career_timing"],
                    "side_business": analysis["side_business"],
                    "wealth_building": analysis["wealth_building"],
                    "work_relationships": analysis["work_relationships"],
                    "luck_improvement": analysis["luck_improvement"],
                },
                "cached": True,
            }
        )

    return items
