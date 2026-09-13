import { useEffect, useState } from 'react';
import { fetchSajuHistory, type SajuHistoryItem } from '../api/saju';
import { ChevronRight } from '../components/icons';
import './HistoryScreen.css';

type HistoryScreenProps = {
  userKey: string;
  onSelect: (item: SajuHistoryItem) => void;
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatPillars(pillars: SajuHistoryItem['pillars']): string {
  const parts = [`${pillars.year}년`, `${pillars.month}월`, `${pillars.day}일`];
  if (pillars.hour) {
    parts.push(`${pillars.hour}시`);
  }
  return parts.join(' ');
}

export function HistoryScreen({ userKey, onSelect }: HistoryScreenProps) {
  const [items, setItems] = useState<SajuHistoryItem[] | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchSajuHistory(userKey)
      .then((result) => {
        if (!cancelled) setItems(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : '알 수 없는 오류가 발생했어요.');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [userKey]);

  return (
    <div className="canvas history-screen">
      <div className="history-screen__content">
        <h1 className="history-screen__title">지난 결과</h1>

        {items === null && !errorMessage && <p className="history-screen__status">불러오는 중…</p>}
        {errorMessage && <p className="history-screen__status">{errorMessage}</p>}
        {items !== null && items.length === 0 && (
          <p className="history-screen__status">아직 조회한 사주가 없어요.</p>
        )}

        {items && items.length > 0 && (
          <div className="history-list">
            {items.map((item) => (
              <button
                type="button"
                key={item.profile_id}
                className="history-row"
                onClick={() => onSelect(item)}
              >
                <span className="history-row__text">
                  <span className="history-row__pillars">{formatPillars(item.pillars)}</span>
                  <span className="history-row__date">{formatDateTime(item.created_at)}</span>
                </span>
                <span className="history-row__icon">
                  <ChevronRight size={20} />
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
