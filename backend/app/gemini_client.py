from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from .config import get_settings
from .saju_calculator import PillarResult
from .schemas import SajuAnalysisResult

CONTEXT_TEMPLATE = """\
당신은 사주명리학 전문가입니다. 아래 사주 원국·명리 분석 데이터를 근거로 질문에
답하세요. 막연한 이야기 대신, 아래 계산된 격국·용신·십신·신살·십이운성·대운
같은 근거를 실제로 활용해서 설명하세요.

중요 — 문체: 독자는 사주명리학을 전혀 모르는 일반인입니다. "정인", "편관",
"양인격" 같은 전문 용어를 그대로 나열하지 마세요. 용어 자체보다 그 의미를
쉬운 일상 언어로 풀어서 설명하고, 꼭 용어를 언급해야 하면 바로 뒤에 괄호로
쉬운 뜻을 붙이세요. 예: "정인(배움과 안정을 뒷받침해주는 기운)이 강해서"가
아니라 "차분히 배우고 준비하면 힘이 되어주는 기운이 강해서"처럼, 용어 없이도
뜻이 통하게 쓰는 쪽을 우선하세요.

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
"""

INSTRUCTION_SUFFIX = """
이 항목은 위 세부 질문에서 가장 중요한 핵심만 골라 2~3문장으로 짧고 명확하게
쓰세요. 세부 질문을 전부 나열하지 말고, 이 사람에게 가장 도움이 될 한두 가지에
집중하세요. 줄바꿈을 나타내는 기호 문자(백슬래시+n 등)를 텍스트로 쓰지 마세요.
"""


class _CareerFitSection(BaseModel):
    career_fit: str


class _CareerTimingSection(BaseModel):
    career_timing: str


class _SideBusinessSection(BaseModel):
    side_business: str


class _WealthBuildingSection(BaseModel):
    wealth_building: str


class _WorkRelationshipsSection(BaseModel):
    work_relationships: str


class _LuckImprovementSection(BaseModel):
    luck_improvement: str


_CAREER_FIT_INSTRUCTIONS = """
career_fit — 타고난 직업·적성 (그릇 진단)
- 조직형 vs 독립형(회사원 vs 프리랜서·사업가 팔자) 중 어느 쪽에 가까운지
- 오행/십신에 근거한 최적의 직무·산업군 추천
- 나에게 맞는 직업 환경(대기업/공공기관/스타트업/1인 비즈니스 중 어느 쪽인지)
"""

_CAREER_TIMING_INSTRUCTIONS = """
career_timing — 타이밍과 이동수 (운의 흐름)
- 위에 명시된 '현재 만 나이'와 '현재 대운'을 근거로 올해 즈음의
  퇴사·이직·시험운(충·극·합 여부)
- 10년 대운으로 보는 커리어 전성기 타이밍이 언제인지(몇 살 대운인지 명시)
- 지금은 버텨야 할 때인지, 판을 엎고 도전해야 할 때인지
"""

_SIDE_BUSINESS_INSTRUCTIONS = """
side_business — 사주 기반 부업·N잡 (숨은 재주 발현)
- 사주의 식상·재성에 근거한 무자본 부업 매칭(콘텐츠/지식/판매/기술형 등)
- 본업의 결핍을 채워주는 보조 파이프라인 추천
"""

_WEALTH_BUILDING_INSTRUCTIONS = """
wealth_building — 재물운과 자산 증식법 (돈의 형태)
- 정재형(따박따박 월급·적금형) vs 편재형(투자·사업·한방형) 중 어느 쪽인지
- 돈이 새어나가는 구멍(군겁쟁재 등)에 대한 방어 가이드
- 나에게 맞는 재테크 방식(부동산/주식/현금흐름 등)
"""

_WORK_RELATIONSHIPS_INSTRUCTIONS = """
work_relationships — 일복과 직장 인간관계 (귀인과 빌런)
- 나를 키워주는 '천을귀인' 상사·동료의 특징
- 피해야 할 악연 유형과 직장 내 처세 가이드
- 만성 야근·번아웃 방어법(사주상 과도한 기운을 완화하는 방법)
"""

_LUCK_IMPROVEMENT_INSTRUCTIONS = """
luck_improvement — 직업 개운법 (막힌 운 뚫기)
- 부족한 오행(용신)을 채우는 직장 일상 루틴
- 일운을 높이는 책상 방향, 행운의 컬러, 숫자
- 일이 풀리지 않을 때 에너지를 바꾸는 행동 요령
"""

# (응답 스키마, 세부 질문 지시문) — 항목마다 별도 호출로 쪼개 전부 동시에
# 실행한다. 항목 하나짜리 출력이라 생성이 더 빨리 끝나고, 병렬이라 전체
# 응답 시간은 가장 느린 항목 하나의 시간에 수렴한다.
_GROUPS: list[tuple[type[BaseModel], str]] = [
    (_CareerFitSection, _CAREER_FIT_INSTRUCTIONS),
    (_CareerTimingSection, _CAREER_TIMING_INSTRUCTIONS),
    (_SideBusinessSection, _SIDE_BUSINESS_INSTRUCTIONS),
    (_WealthBuildingSection, _WEALTH_BUILDING_INSTRUCTIONS),
    (_WorkRelationshipsSection, _WORK_RELATIONSHIPS_INSTRUCTIONS),
    (_LuckImprovementSection, _LUCK_IMPROVEMENT_INSTRUCTIONS),
]

ModelT = TypeVar("ModelT", bound=BaseModel)


def _new_client() -> genai.Client:
    # 매 호출(스레드)마다 새 클라이언트를 만든다 — google-genai의 내부 httpx
    # 클라이언트를 여러 스레드가 공유하면 "client has been closed" 오류가 난다
    # (동시 호출로 재현됨). 클라이언트 생성 자체는 가벼워 비용이 작다.
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


def _build_context(gender: str, pillars: PillarResult) -> str:
    return CONTEXT_TEMPLATE.format(
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


def _strip_literal_escapes(result: ModelT) -> ModelT:
    """Gemini가 가끔 실제 개행 대신 문자 그대로의 '\\n'을 출력하는 경우를 보정한다."""
    cleaned = {
        field_name: value.replace("\\n", "\n") if isinstance(value, str) else value
        for field_name, value in result.model_dump().items()
    }
    return type(result)(**cleaned)


def _call_group(context: str, schema_cls: type[ModelT], instructions: str) -> ModelT:
    settings = get_settings()
    prompt = f"{context}\n다음 항목을 위 형식대로 작성하세요.\n{instructions}\n{INSTRUCTION_SUFFIX}"

    # google-genai의 httpx 클라이언트는 GC될 때 스스로를 닫는다(__del__) — 아래처럼
    # 변수에 담아두지 않고 `_new_client().models.generate_content(...)`로 체이닝하면
    # 요청이 끝나기 전에 클라이언트가 회수돼 "client has been closed" 오류가 난다.
    client = _new_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema_cls,
            # 명리학 계산(격국·용신·대운 등)은 이미 Python에서 끝냈고 Gemini는 그
            # 사실을 문장으로 풀어쓰기만 하면 된다 — thinking을 켜두면 이 정도
            # 작업에도 내부 추론에 20초 이상을 써서 체감 속도가 크게 느려진다
            # (실측: thinking on 30초 vs off 5.5초, 같은 프롬프트).
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return _strip_literal_escapes(schema_cls.model_validate_json(response.text))


def analyze_saju(*, gender: str, pillars: PillarResult) -> SajuAnalysisResult:
    context = _build_context(gender, pillars)

    with ThreadPoolExecutor(max_workers=len(_GROUPS)) as executor:
        futures = [executor.submit(_call_group, context, schema_cls, instructions) for schema_cls, instructions in _GROUPS]
        sections = [future.result() for future in futures]

    merged: dict[str, str] = {}
    for section in sections:
        merged.update(section.model_dump())
    return SajuAnalysisResult(**merged)
