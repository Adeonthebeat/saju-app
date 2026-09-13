import { User } from '@apps-in-toss/web-framework';

/**
 * 앱인토스 SDK가 앱-사용자 단위로 발급하는 익명 식별 해시.
 * 미지원 앱 버전이거나 발급이 거부되면 null을 반환한다 — 이 경우 조회 이력
 * 기능만 못 쓸 뿐, 사주 분석 자체는 그대로 동작해야 한다(로그인 강제 금지).
 */
export async function getUserKey(): Promise<string | null> {
  try {
    const result = await User.getAnonymousKey();
    return result?.hash ?? null;
  } catch {
    return null;
  }
}
