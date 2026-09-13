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

export function ResultScreen({ result, onRestart, restartLabel = '다시 입력하기' }: ResultScreenProps) {
  return (
    <div className="canvas result-screen">
      <div className="result-screen__content">
        <p className="result-screen__notice">참고용 콘텐츠예요. 진로·투자 결정은 전문가와 상담해주세요.</p>

        {result.cached && <span className="result-screen__badge">이미 분석된 사주예요</span>}

        {SECTIONS.map((section) => (
          <div className="result-card" key={section.key}>
            <h2 className="result-card__title">{section.title}</h2>
            <p className="result-card__body">{result.analysis[section.key]}</p>
          </div>
        ))}
      </div>

      <div className="result-screen__cta">
        <button type="button" className="secondary-button" onClick={onRestart}>
          {restartLabel}
        </button>
      </div>
    </div>
  );
}
