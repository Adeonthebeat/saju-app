from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from functools import lru_cache

from korean_saju import Daewoon, Gender, Saju, SajuAnalysis, SajuPosition, load_bundled_data

# 서울 기준 경도 (진태양시 보정용). 출생지를 입력받게 되면 이 값을 대체한다.
SEOUL_LONGITUDE = 126.9784

FIVE_ELEMENTS = ("목", "화", "토", "금", "수")

# 대운은 앞으로 6개(60년치)만 본다 — 프롬프트에 다 담기엔 충분하고 과하지 않은 양.
DAEWOON_COUNT = 6


class SajuCalculationError(Exception):
    """사주 계산이 불가능한 입력일 때 (예: 음력 변환 범위 밖)."""


@lru_cache(maxsize=1)
def _bundled_data():
    return load_bundled_data()


def _to_solar_datetime(
    birth_date: date,
    birth_time: time | None,
    calendar: str,
    is_lunar_leap_month: bool,
) -> datetime:
    lunar, _ = _bundled_data()
    # 시간을 모르면 자정 경계 오차를 피하기 위해 정오를 기준으로 계산한다.
    # 연/월/일주는 정오 기준으로 계산해도 바뀌지 않고, 시주만 별도로 비운다.
    nominal_time = birth_time or time(12, 0)

    if calendar == "lunar":
        solar_date = lunar.lunar_to_solar(
            year=birth_date.year,
            month=birth_date.month,
            day=birth_date.day,
            is_leap=is_lunar_leap_month,
        )
        if solar_date is None:
            raise SajuCalculationError(
                "음력 날짜를 양력으로 변환할 수 없습니다 (지원 범위: 1900~2050년)."
            )
        return datetime.combine(solar_date.date(), nominal_time)

    return datetime.combine(birth_date, nominal_time)


@dataclass
class ShipsinEntry:
    position: str  # 년/월/일/시
    cheon_gan: str | None  # 일간 자리는 비교 기준이라 천간 십신이 없다
    ji_ji: str | None


@dataclass
class SinsalEntry:
    name: str
    description: str
    kind: str  # "길신" | "흉신"


@dataclass
class SibiunseongEntry:
    position: str
    name: str
    description: str


@dataclass
class DaewoonEntry:
    start_age: int
    gan_ji: str


@dataclass
class PillarResult:
    year_pillar: str
    month_pillar: str
    day_pillar: str
    hour_pillar: str | None
    five_elements: dict[str, int]
    # 아래는 팔자 조합(캐시 키)에서 파생되는 추가 명리 정보 — Gemini 프롬프트를
    # 구체적으로 채우는 근거 데이터다. 캐시 키 자체에는 영향을 주지 않는다.
    jeonggyeok: str = ""
    yongsin: str = ""
    shipsin: list[ShipsinEntry] = field(default_factory=list)
    sinsal: list[SinsalEntry] = field(default_factory=list)
    sibiunseong: list[SibiunseongEntry] = field(default_factory=list)
    daewoon_direction: str = ""  # "순행" | "역행"
    daewoon: list[DaewoonEntry] = field(default_factory=list)
    # "지금 몇 살/무슨 대운인지"는 팔자 조합과 무관하게 매 요청 시점(오늘 날짜)에
    # 따라 달라지므로 캐시하지 않고, 매번 이 함수 호출 시점 기준으로 계산한다.
    today: date = field(default_factory=date.today)
    current_age: int = 0
    current_daewoon: DaewoonEntry | None = None


def calculate_pillars(
    *,
    birth_date: date,
    birth_time: time | None,
    is_time_unknown: bool,
    calendar: str,
    gender: str,
    is_lunar_leap_month: bool = False,
    longitude: float = SEOUL_LONGITUDE,
) -> PillarResult:
    """생년월일시+성별로 사주팔자와 명리 분석 근거 데이터를 계산한다.

    시간을 모르는 경우 시주는 계산하지 않고 연/월/일주 3기둥만 반환한다.
    """
    _, solar_terms = _bundled_data()
    kst_moment = _to_solar_datetime(birth_date, birth_time, calendar, is_lunar_leap_month)

    saju = Saju.from_birth(kst_moment=kst_moment, solar_terms=solar_terms, longitude=longitude)

    known_hour = not is_time_unknown and birth_time is not None
    pillars = [saju.year_pillar, saju.month_pillar, saju.day_pillar]
    if known_hour:
        pillars.append(saju.hour_pillar)

    counts = {element: 0 for element in FIVE_ELEMENTS}
    for pillar in pillars:
        counts[pillar.cheon_gan.o_haeng.hangul] += 1
        counts[pillar.ji_ji.o_haeng.hangul] += 1

    analysis = SajuAnalysis(saju)

    shipsin = [
        ShipsinEntry(
            position=position.hangul,
            cheon_gan=cg.hangul if (cg := analysis.cheon_gan_shipsin.get(position)) else None,
            ji_ji=jj.hangul if (jj := analysis.ji_ji_shipsin.get(position)) else None,
        )
        for position in SajuPosition
        if position != SajuPosition.HOUR or known_hour
    ]

    sinsal = [
        SinsalEntry(
            name=detection.sinsal.hangul,
            description=detection.sinsal.description,
            kind="길신" if detection.sinsal.is_gilsin else "흉신",
        )
        for detection in analysis.sinsal
    ]

    sibiunseong = [
        SibiunseongEntry(position=position.hangul, name=value.hangul, description=value.description)
        for position, value in analysis.sibiunseong.items()
        if position != SajuPosition.HOUR or known_hour
    ]

    daewoon = Daewoon.compute(saju=saju, gender=Gender(gender), solar_terms=solar_terms, count=DAEWOON_COUNT)
    daewoon_entries = [
        DaewoonEntry(start_age=entry.start_age, gan_ji=entry.gan_ji.hangul) for entry in daewoon.entries
    ]

    # "지금 몇 살이고 어느 대운인지"는 Gemini가 추측하게 두지 않고 여기서 사실로
    # 확정한다 — 만 나이는 실제 태어난(양력 환산) 날짜 기준으로 센다.
    solar_birth_date = kst_moment.date()
    today = date.today()
    current_age = today.year - solar_birth_date.year - (
        (today.month, today.day) < (solar_birth_date.month, solar_birth_date.day)
    )
    current_daewoon = None
    for entry in daewoon_entries:
        if entry.start_age <= current_age:
            current_daewoon = entry
        else:
            break

    return PillarResult(
        year_pillar=saju.year_pillar.hangul,
        month_pillar=saju.month_pillar.hangul,
        day_pillar=saju.day_pillar.hangul,
        hour_pillar=saju.hour_pillar.hangul if known_hour else None,
        five_elements=counts,
        jeonggyeok=str(analysis.jeonggyeok),
        yongsin=str(analysis.yongsin),
        shipsin=shipsin,
        sinsal=sinsal,
        sibiunseong=sibiunseong,
        daewoon_direction="순행" if daewoon.forward else "역행",
        daewoon=daewoon_entries,
        today=today,
        current_age=current_age,
        current_daewoon=current_daewoon,
    )
