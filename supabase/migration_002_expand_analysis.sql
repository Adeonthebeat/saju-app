-- 분석 결과를 4개 항목 → 6개 항목으로 확장하면서 컬럼명을 재정리한다.
-- 기존 saju_analyses 데이터(테스트 데이터)는 새 형식과 호환되지 않으므로 비운다.

truncate table saju_analyses;

alter table saju_analyses
    drop column if exists career_aptitude,
    drop column if exists personality_type,
    add column if not exists career_fit text,          -- 1) 타고난 직업·적성 (그릇 진단)
    add column if not exists career_timing text,        -- 2) 타이밍과 이동수 (운의 흐름)
    add column if not exists work_relationships text,   -- 5) 일복과 직장 인간관계
    add column if not exists luck_improvement text;     -- 6) 직업 개운법

comment on column saju_analyses.side_business is '3) 사주 기반 부업·N잡';
comment on column saju_analyses.wealth_building is '4) 재물운과 자산 증식법';
