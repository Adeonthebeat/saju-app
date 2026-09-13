-- ============================================================================
-- "나 뭐하고 먹고 살지?" 서비스용 Supabase 스키마
--
-- 흐름:
--   1) 사용자가 생년월일시 + 성별을 입력
--   2) 파이썬 백엔드가 사주 계산 라이브러리로 사주팔자(연/월/일/시주)를 산출
--   3) 산출된 팔자 조합이 saju_charts 에 이미 있는지 확인
--        - 있으면: 저장된 saju_analyses 를 그대로 재사용 (Gemini 재호출 안 함)
--        - 없으면: saju_charts 에 새로 저장 → Gemini API 호출 → saju_analyses 에 1회 저장
--   4) 사용자의 입력 이벤트 자체는 saju_profiles 에 남기고 saju_chart_id 로 연결
--
-- 핵심 설계: 사주 분석(Gemini 호출)은 "같은 생년월일시+성별"을 입력한 모든 사용자가
-- 공유한다. 분석은 사용자 단위가 아니라 팔자 조합(saju_charts) 단위로 딱 한 번만 수행한다.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- ENUM 타입
-- ---------------------------------------------------------------------------
create type gender_type as enum ('male', 'female');
create type calendar_type as enum ('solar', 'lunar');        -- 양력 / 음력
create type analysis_status as enum ('pending', 'completed', 'failed');

-- ---------------------------------------------------------------------------
-- saju_charts: 계산된 사주팔자 조합 자체 (사용자와 무관, 팔자 조합당 1행)
--   동일한 (연주,월주,일주,시주,성별) 조합은 여러 사용자가 공유한다.
-- ---------------------------------------------------------------------------
create table saju_charts (
    id                uuid primary key default gen_random_uuid(),

    gender            gender_type not null,
    year_pillar       text not null,            -- 예: "갑자"
    month_pillar      text not null,
    day_pillar        text not null,
    hour_pillar       text,                     -- 시간 모르면 null
    is_time_unknown   boolean not null default false,

    -- 오행 분포 등 부가 계산 결과 {"목":1,"화":2,"토":2,"금":2,"수":1} 형태
    five_elements     jsonb,

    created_at        timestamptz not null default now()
);

-- 같은 팔자 조합 중복 저장 방지 (hour_pillar가 null이어도 유일성 판정되도록 coalesce)
create unique index idx_saju_charts_unique
    on saju_charts (gender, year_pillar, month_pillar, day_pillar, coalesce(hour_pillar, ''));

-- ---------------------------------------------------------------------------
-- saju_analyses: 팔자 조합(saju_charts) 1건당 Gemini 분석 결과 1건 (재사용 캐시)
-- ---------------------------------------------------------------------------
create table saju_analyses (
    id                  uuid primary key default gen_random_uuid(),
    saju_chart_id       uuid not null references saju_charts(id) on delete cascade,

    status              analysis_status not null default 'pending',

    -- 6가지 분석 결과
    career_fit          text,     -- 1) 타고난 직업·적성 (그릇 진단)
    career_timing       text,     -- 2) 타이밍과 이동수 (운의 흐름)
    side_business       text,     -- 3) 사주 기반 부업·N잡
    wealth_building     text,     -- 4) 재물운과 자산 증식법
    work_relationships  text,     -- 5) 일복과 직장 인간관계
    luck_improvement    text,     -- 6) 직업 개운법

    -- 재현/디버깅을 위한 메타데이터
    gemini_model        text,             -- 예: "gemini-2.5-pro"
    prompt_version      text,             -- 프롬프트 템플릿 버전 관리용
    gemini_raw_response jsonb,            -- Gemini 원본 응답 전체 보관
    error_message       text,             -- status='failed'일 때 원인 기록

    created_at          timestamptz not null default now(),
    completed_at        timestamptz
);

-- 팔자 조합 1건당 분석 결과는 항상 1건만 존재 (있으면 재사용, 없으면 생성)
create unique index idx_saju_analyses_chart_id_unique on saju_analyses(saju_chart_id);
create index idx_saju_analyses_status on saju_analyses(status);

-- ---------------------------------------------------------------------------
-- saju_profiles: 사용자의 입력 이벤트 기록 (조회 이력용, 분석 결과는 저장하지 않음)
-- ---------------------------------------------------------------------------
create table saju_profiles (
    id                uuid primary key default gen_random_uuid(),

    -- 앱인토스 SDK User.getAnonymousKey()가 발급하는 앱-사용자 단위 익명 해시.
    -- Supabase Auth를 쓰지 않으므로 auth.users를 참조하지 않는다. 발급 실패/거부
    -- 시 null 허용(그 경우 조회 이력 기능만 못 쓴다).
    user_key          text,

    -- 사용자 입력값 원본 (계산 재현·디버깅용)
    birth_date        date not null,
    birth_time        time,
    is_time_unknown   boolean not null default false,
    calendar          calendar_type not null default 'solar',
    gender            gender_type not null,

    -- 이 입력이 산출한 팔자 조합 (분석 결과는 여기서 조인해서 가져온다)
    saju_chart_id     uuid not null references saju_charts(id),

    created_at        timestamptz not null default now()
);

create index idx_saju_profiles_user_key on saju_profiles(user_key);
create index idx_saju_profiles_chart_id on saju_profiles(saju_chart_id);

-- ---------------------------------------------------------------------------
-- Row Level Security
--   - 백엔드(Python)는 service_role 키로 접근 → RLS 영향을 받지 않고 자유롭게 write
--   - 클라이언트는 이 테이블들에 직접 접근하지 않고 항상 백엔드를 거친다. Supabase
--     Auth(auth.uid())를 쓰지 않으므로 "본인 것만 조회" 제약은 여기(RLS)가 아니라
--     백엔드가 user_key로 필터링하는 애플리케이션 계층에서 강제한다.
-- ---------------------------------------------------------------------------
alter table saju_charts enable row level security;
alter table saju_analyses enable row level security;
alter table saju_profiles enable row level security;

-- select 정책을 두지 않는다 → anon/authenticated 키로는 아무것도 읽을 수 없다.
-- insert/update/delete 정책도 없음 → 백엔드는 service_role 키로 RLS를 우회해 쓴다.
