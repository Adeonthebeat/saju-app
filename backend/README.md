# backend

사주 계산(`korean-saju`) → Gemini 분석(팔자 조합당 1회, DB 캐시) → Supabase 저장을 담당하는 FastAPI 서버.

## 준비

```bash
python3.13 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / GEMINI_API_KEY 채우기
```

DB 스키마는 `../supabase/schema.sql`을 Supabase 프로젝트에 먼저 적용해야 한다.

## 실행

```bash
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

- `GET /health` — 헬스체크
- `POST /api/saju/analyze` — 생년월일시+성별 입력 → 사주 계산 → (캐시 없으면 Gemini 분석) → 저장 → 4가지 결과 반환
- `GET /api/saju/history?user_id=<uuid>` — 특정 사용자의 조회 이력 + 분석 결과

API 문서: `http://localhost:8000/docs`

## 구조

```
app/
  main.py              FastAPI 앱 진입점
  config.py            환경변수 (.env) 로딩
  schemas.py           요청/응답 Pydantic 모델
  saju_calculator.py   korean-saju 라이브러리로 팔자·오행 계산
  gemini_client.py     Gemini API 호출 + 구조화 출력 파싱
  supabase_client.py   service_role 키 Supabase 클라이언트
  repository.py        saju_charts/saju_analyses 캐시 조회·생성, saju_profiles 기록
  routers/saju.py      /api/saju/* 엔드포인트
```

## 캐싱 동작

같은 (성별, 연주, 월주, 일주, 시주) 조합은 `saju_charts`에서 단 1행만 존재하고,
그 조합의 Gemini 분석 결과도 `saju_analyses`에 1행만 존재한다. 이미 분석된 조합이
다시 들어오면 Gemini를 호출하지 않고 저장된 결과를 그대로 반환한다
(`SajuAnalyzeResponse.cached`로 캐시 히트 여부 확인 가능).
