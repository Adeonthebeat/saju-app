const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export type Gender = 'male' | 'female';
export type Calendar = 'solar' | 'lunar';

export type SajuAnalyzeRequest = {
  user_key: string | null;
  birth_date: string; // YYYY-MM-DD
  birth_time: string | null; // HH:MM:SS
  is_time_unknown: boolean;
  calendar: Calendar;
  gender: Gender;
};

export type SajuAnalysis = {
  career_fit: string;
  career_timing: string;
  side_business: string;
  wealth_building: string;
  work_relationships: string;
  luck_improvement: string;
};

export type SajuAnalyzeResponse = {
  profile_id: string;
  chart_id: string;
  pillars: {
    year: string;
    month: string;
    day: string;
    hour: string | null;
  };
  five_elements: Record<string, number>;
  analysis: SajuAnalysis;
  cached: boolean;
};

export type SajuHistoryItem = SajuAnalyzeResponse & {
  created_at: string;
};

export async function analyzeSaju(payload: SajuAnalyzeRequest): Promise<SajuAnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/saju/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? '사주 분석 요청이 실패했어요. 잠시 후 다시 시도해주세요.');
  }

  return response.json();
}

export async function fetchSajuHistory(userKey: string): Promise<SajuHistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/saju/history?${new URLSearchParams({ user_key: userKey })}`);

  if (!response.ok) {
    throw new Error('지난 결과를 불러오지 못했어요. 잠시 후 다시 시도해주세요.');
  }

  return response.json();
}
