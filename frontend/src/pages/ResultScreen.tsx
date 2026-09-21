import { Share } from '@apps-in-toss/web-framework';
import { useState } from 'react';
import type { SajuAnalyzeResponse } from '../api/saju';
import './ResultScreen.css';

type ResultScreenProps = {
  result: SajuAnalyzeResponse;
  onRestart: () => void;
  restartLabel?: string;
};

const SECTIONS: Array<{ key: keyof SajuAnalyzeResponse['analysis']; title: string }> = [
  { key: 'career_fit', title: '타고난 직업·적성' },
  { key: 'career_timing', title: '타이밍과 이동수' },
  { key: 'side_business', title: '사주 기반 부업·N잡' },
  { key: 'wealth_building', title: '재물운과 자산 증식법' },
  { key: 'work_relationships', title: '일복과 직장 인간관계' },
  { key: 'luck_improvement', title: '직업 개운법' },
];

const APP_PATH = 'intoss://ade20260906';

export function ResultScreen({ result, onRestart, restartLabel = '다시 입력하기' }: ResultScreenProps) {
  const [shareError, setShareError] = useState<string | null>(null);

  const handleShare = async () => {
    setShareError(null);
    try {
      const link = await Share.createLink({ path: APP_PATH });
      await Share.sendMessage({
        message: `나 뭐하고 먹고 살지? 사주로 진로·재테크 성향을 알아봤어요. 궁금하면 한번 해보세요!\n${link}`,
      });
    } catch {
      setShareError('지금은 공유할 수 없어요. 잠시 후 다시 시도해주세요.');
    }
  };

  return (
    <div className="canvas result-screen">
      <div className="result-screen__content">
        <p className="result-screen__notice">참고용 콘텐츠예요. 진로·투자 결정은 전문가와 상담해주세요.</p>

        {result.cached && <span className="result-screen__badge">이미 분석된 사주예요</span>}

        <div className="result-pillars">
          <h2 className="result-pillars__title">내 사주 원국</h2>
          <div className="result-pillars__row">
            <span className="result-pillars__chip">연주 {result.pillars.year}</span>
            <span className="result-pillars__chip">월주 {result.pillars.month}</span>
            <span className="result-pillars__chip">일주 {result.pillars.day}</span>
            <span className="result-pillars__chip">시주 {result.pillars.hour ?? '모름'}</span>
          </div>
          <div className="result-pillars__row">
            {Object.entries(result.five_elements).map(([element, count]) => (
              <span className="result-pillars__chip result-pillars__chip--element" key={element}>
                {element} {count}
              </span>
            ))}
          </div>
        </div>

        {SECTIONS.map((section) => (
          <div className="result-card" key={section.key}>
            <h2 className="result-card__title">{section.title}</h2>
            <p className="result-card__body">{result.analysis[section.key]}</p>
          </div>
        ))}

        {shareError && <p className="result-screen__error">{shareError}</p>}
      </div>

      <div className="result-screen__cta">
        <button type="button" className="secondary-button" onClick={onRestart}>
          {restartLabel}
        </button>
        <button type="button" className="primary-button" onClick={handleShare}>
          친구에게 공유하기
        </button>
      </div>
    </div>
  );
}
