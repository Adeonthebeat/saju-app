from functools import lru_cache

from google import genai
from google.genai import types

from .config import get_settings
from .saju_calculator import PillarResult
from .schemas import SajuAnalysisResult

PROMPT_TEMPLATE = """\
당신은 사주명리학 전문가입니다. 아래 사주 원국·명리 분석 데이터를 근거로,
이 사람에게 실질적으로 도움이 되는 6개 항목을 작성하세요. 각 항목은 아래 나열된
세부 질문에 전부 답하는 여러 문단(또는 줄바꿈으로 구분된 여러 항목)으로,
각 3~6문장 이상 충분히 구체적이고 길게 작성하세요. 막연한 이야기 대신, 위에서
계산된 격국·용신·십신·신살·십이운성·대운 같은 근거를 실제로 인용하며 설명하세요.

[사주 원국]
성별: {gender}
연주: {year_pillar} / 월주: {month_pillar} / 일주: {day_pillar} / 시주: {hour_pillar}
오행 분포: {five_elements}
격국: {jeonggyeok}
용신: {yongsin}

[현재 시점 — 반드시 이 값을 그대로 쓰고, 나이나 대운 시기를 임의로 가정하지 마세요]
오늘 날짜: {today}
현재 만 나이: {current_age}세
현재 대운: {current_daewoon}

[십신 (일간 기준 각 기둥의 관계)]
{shipsin_text}

[십이운성]
{sibiunseong_text}

[신살]
{sinsal_text}

[대운] ({daewoon_direction})
{daewoon_text}

다음 6개 항목을 각각 위 형식대로 작성하세요. 문단을 나눌 때는 실제 줄바꿈만
쓰고, 줄바꿈을 나타내는 기호 문자(백슬래시+n 등)를 텍스트로 쓰지 마세요.

1. career_fit — 타고난 직업·적성 (그릇 진단)
   - 조직형 vs 독립형(회사원 vs 프리랜서·사업가 팔자) 중 어느 쪽에 가까운지
   - 오행/십신에 근거한 최적의 직무·산업군 추천
   - 나에게 맞는 직업 환경(대기업/공공기관/스타트업/1인 비즈니스 중 어느 쪽인지)

2. career_timing — 타이밍과 이동수 (운의 흐름)
   - 위에 명시된 '현재 만 나이'와 '현재 대운'을 근거로 올해 즈음의
     퇴사·이직·시험운(충·극·합 여부)
   - 10년 대운으로 보는 커리어 전성기 타이밍이 언제인지(몇 살 대운인지 명시)
   - 지금은 버텨야 할 때인지, 판을 엎고 도전해야 할 때인지

3. side_business — 사주 기반 부업·N잡 (숨은 재주 발현)
   - 사주의 식상·재성에 근거한 무자본 부업 매칭(콘텐츠/지식/판매/기술형 등)
   - 본업의 결핍을 채워주는 보조 파이프라인 추천

4. wealth_building — 재물운과 자산 증식법 (돈의 형태)
   - 정재형(따박따박 월급·적금형) vs 편재형(투자·사업·한방형) 중 어느 쪽인지
   - 돈이 새어나가는 구멍(군겁쟁재 등)에 대한 방어 가이드
   - 나에게 맞는 재테크 방식(부동산/주식/현금흐름 등)

5. work_relationships — 일복과 직장 인간관계 (귀인과 빌런)
   - 나를 키워주는 '천을귀인' 상사·동료의 특징
   - 피해야 할 악연 유형과 직장 내 처세 가이드
   - 만성 야근·번아웃 방어법(사주상 과도한 기운을 완화하는 방법)

6. luck_improvement — 직업 개운법 (막힌 운 뚫기)
   - 부족한 오행(용신)을 채우는 직장 일상 루틴
   - 일운을 높이는 책상 방향, 행운의 컬러, 숫자
   - 일이 풀리지 않을 때 에너지를 바꾸는 행동 요령
"""


@lru_cache
def _client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _format_shipsin(pillars: PillarResult) -> str:
    lines = []
    for entry in pillars.shipsin:
        parts = []
        if entry.cheon_gan:
            parts.append(f"천간={entry.cheon_gan}")
        if entry.ji_ji:
            parts.append(f"지지={entry.ji_ji}")
        lines.append(f"- {entry.position}주: {', '.join(parts)}")
    return "\n".join(lines) if lines else "(정보 없음)"


def _format_sibiunseong(pillars: PillarResult) -> str:
    lines = [f"- {e.position}주: {e.name} ({e.description})" for e in pillars.sibiunseong]
    return "\n".join(lines) if lines else "(정보 없음)"


def _format_sinsal(pillars: PillarResult) -> str:
    lines = [f"- {e.name}[{e.kind}]: {e.description}" for e in pillars.sinsal]
    return "\n".join(lines) if lines else "(해당 신살 없음)"


def _format_daewoon(pillars: PillarResult) -> str:
    lines = [f"- {e.start_age}세~: {e.gan_ji}" for e in pillars.daewoon]
    return "\n".join(lines) if lines else "(정보 없음)"


def _format_current_daewoon(pillars: PillarResult) -> str:
    if pillars.current_daewoon is None:
        return "아직 첫 대운 시작 전(유년기)"
    return f"{pillars.current_daewoon.gan_ji} ({pillars.current_daewoon.start_age}세~)"


def _strip_literal_escapes(result: SajuAnalysisResult) -> SajuAnalysisResult:
    """Gemini가 가끔 실제 개행 대신 문자 그대로의 '\\n'을 출력하는 경우를 보정한다."""
    cleaned = {
        field_name: value.replace("\\n", "\n") if isinstance(value, str) else value
        for field_name, value in result.model_dump().items()
    }
    return SajuAnalysisResult(**cleaned)


def analyze_saju(*, gender: str, pillars: PillarResult) -> SajuAnalysisResult:
    settings = get_settings()

    prompt = PROMPT_TEMPLATE.format(
        gender="남성" if gender == "male" else "여성",
        year_pillar=pillars.year_pillar,
        month_pillar=pillars.month_pillar,
        day_pillar=pillars.day_pillar,
        hour_pillar=pillars.hour_pillar or "모름",
        five_elements=pillars.five_elements,
        jeonggyeok=pillars.jeonggyeok,
        yongsin=pillars.yongsin,
        today=pillars.today.isoformat(),
        current_age=pillars.current_age,
        current_daewoon=_format_current_daewoon(pillars),
        shipsin_text=_format_shipsin(pillars),
        sibiunseong_text=_format_sibiunseong(pillars),
        sinsal_text=_format_sinsal(pillars),
        daewoon_direction=pillars.daewoon_direction,
        daewoon_text=_format_daewoon(pillars),
    )

    response = _client().models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SajuAnalysisResult,
        ),
    )
    return _strip_literal_escapes(SajuAnalysisResult.model_validate_json(response.text))
