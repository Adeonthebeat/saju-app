import { type FormEvent, useEffect, useState } from 'react';
import type { Calendar, Gender, SajuAnalyzeRequest } from '../api/saju';
import { ChevronRight } from '../components/icons';
import './InputScreen.css';

type InputScreenProps = {
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: Omit<SajuAnalyzeRequest, 'user_key'>) => void;
  onOpenHistory?: () => void;
};

function SegmentedButton({
  label,
  pressed,
  onClick,
}: {
  label: string;
  pressed: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" className="segmented-button" aria-pressed={pressed} onClick={onClick}>
      {label}
    </button>
  );
}

export function InputScreen({ isSubmitting, errorMessage, onSubmit, onOpenHistory }: InputScreenProps) {
  const [gender, setGender] = useState<Gender>('male');
  const [calendar, setCalendar] = useState<Calendar>('solar');
  const [birthDate, setBirthDate] = useState('');
  const [isTimeUnknown, setIsTimeUnknown] = useState(false);
  const [birthTime, setBirthTime] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isTakingLong, setIsTakingLong] = useState(false);

  useEffect(() => {
    if (!isSubmitting) return;
    const timer = window.setTimeout(() => setIsTakingLong(true), 8000);
    return () => window.clearTimeout(timer);
  }, [isSubmitting]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!birthDate) {
      setValidationError('생년월일을 입력해주세요.');
      return;
    }
    if (!isTimeUnknown && !birthTime) {
      setValidationError('태어난 시간을 입력하거나, 시간을 모른다면 위 체크박스를 눌러주세요.');
      return;
    }
    setValidationError(null);
    setIsTakingLong(false);

    onSubmit({
      birth_date: birthDate,
      birth_time: isTimeUnknown ? null : `${birthTime}:00`,
      is_time_unknown: isTimeUnknown,
      calendar,
      gender,
    });
  };

  const displayError = validationError ?? errorMessage;

  return (
    <div className="canvas input-screen">
      <form className="input-screen__content" onSubmit={handleSubmit} id="saju-input-form">
        <div>
          <h1 className="input-screen__title">나 뭐하고 먹고 살지?</h1>
          <p className="input-screen__subtitle">
            생년월일로 알아보는 나의 직업·부업·재테크·유형
          </p>
          {onOpenHistory && (
            <button type="button" className="input-screen__history-link" onClick={onOpenHistory}>
              지난 결과 다시 보기
              <ChevronRight size={18} />
            </button>
          )}
        </div>

        <div className="field-group">
          <span className="field-group__label">성별</span>
          <div className="segmented" role="radiogroup" aria-label="성별">
            <SegmentedButton label="남성" pressed={gender === 'male'} onClick={() => setGender('male')} />
            <SegmentedButton label="여성" pressed={gender === 'female'} onClick={() => setGender('female')} />
          </div>
        </div>

        <div className="field-group">
          <span className="field-group__label">양력 / 음력</span>
          <div className="segmented" role="radiogroup" aria-label="양력 또는 음력">
            <SegmentedButton label="양력" pressed={calendar === 'solar'} onClick={() => setCalendar('solar')} />
            <SegmentedButton label="음력" pressed={calendar === 'lunar'} onClick={() => setCalendar('lunar')} />
          </div>
        </div>

        <div className="field-group">
          <label className="field-group__label" htmlFor="birth-date">
            생년월일
          </label>
          <input
            id="birth-date"
            type="date"
            className="text-input"
            value={birthDate}
            onChange={(event) => setBirthDate(event.target.value)}
            required
          />
        </div>

        <div className="field-group">
          <label className="checkbox-row" htmlFor="time-unknown">
            <input
              id="time-unknown"
              type="checkbox"
              checked={isTimeUnknown}
              onChange={(event) => setIsTimeUnknown(event.target.checked)}
            />
            <span>태어난 시간을 몰라요</span>
          </label>
        </div>

        {!isTimeUnknown && (
          <div className="field-group">
            <label className="field-group__label" htmlFor="birth-time">
              태어난 시간
            </label>
            <input
              id="birth-time"
              type="time"
              className="text-input"
              value={birthTime}
              onChange={(event) => setBirthTime(event.target.value)}
              required
            />
          </div>
        )}

        {displayError && <p className="input-screen__error">{displayError}</p>}
      </form>

      <div className="input-screen__cta">
        {isSubmitting && (
          <p className="input-screen__loading-hint">
            {isTakingLong
              ? '서버가 오랜만에 깨어나는 중일 수 있어요. 최대 30초 정도 걸릴 수 있어요.'
              : '사주를 분석하고 있어요. 잠시만 기다려주세요.'}
          </p>
        )}
        <button type="submit" form="saju-input-form" className="primary-button" disabled={isSubmitting}>
          {isSubmitting ? '분석하는 중…' : '사주 분석하기'}
        </button>
      </div>
    </div>
  );
}
