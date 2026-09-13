-- 사용자 식별 방식을 Supabase Auth(auth.users) 대신 앱인토스 SDK의
-- User.getAnonymousKey() 해시로 전환한다.
--
-- 이유: 이 미니앱은 Supabase Auth로 로그인하지 않는다. 실제 사용자 식별은
-- 앱인토스 SDK가 앱-사용자 단위로 발급하는 익명 해시(User.getAnonymousKey)로
-- 이루어지므로, saju_profiles.user_id(uuid, auth.users 참조)는 애초에 채워질 일이
-- 없었다. 이 해시를 그대로 담을 수 있도록 text 컬럼으로 바꾸고 이름도 user_key로
-- 바꾼다.

-- 기존 auth.uid() 기반 RLS 정책이 user_id 컬럼을 참조하고 있어서, 타입을 바꾸기
-- 전에 정책부터 먼저 지워야 한다(안 그러면 "cannot alter type of a column used
-- in a policy definition" 에러가 난다). 이 정책들은 Supabase Auth를 쓰지 않는
-- 이상 항상 거짓이라 사실상 전면 차단 정책이었다. 클라이언트는 이 테이블들에
-- 직접 접근하지 않고 항상 백엔드(service_role)를 거치므로, "본인 것만 조회"
-- 제약은 애플리케이션 계층(백엔드가 user_key로 필터링)에서 강제한다.
drop policy if exists "select own saju_profiles" on saju_profiles;
drop policy if exists "select own saju_charts" on saju_charts;
drop policy if exists "select own saju_analyses" on saju_analyses;

alter table saju_profiles drop constraint if exists saju_profiles_user_id_fkey;
alter table saju_profiles alter column user_id type text using user_id::text;
alter table saju_profiles rename column user_id to user_key;

alter index if exists idx_saju_profiles_user_id rename to idx_saju_profiles_user_key;
