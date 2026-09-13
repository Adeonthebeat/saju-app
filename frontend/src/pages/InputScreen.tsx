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

function NumberSelect({
  value,
  onChange,
  options,
  placeholder,
  ariaLabel,
  pad = false,
  wide = false,
}: {
  value: string;
  onChange: (value: string) => void;
  options: number[];
  placeholder: string;
  ariaLabel: string;
  pad?: boolean;
  wide?: boolean;
}) {
  return (
    <select
      className={wide ? 'select-input select-input--wide' : 'select-input'}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={ariaLabel}
      required
    >
      <option value="" disabled>
        {placeholder}
      </option>
      {options.map((option) => (
        <option key={option} value={String(option)}>
          {pad ? String(option).padStart(2, '0') : option}
        </option>
      ))}
    </select>
  );
}

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: CURRENT_YEAR - 1900 + 1 }, (_, i) => CURRENT_YEAR - i);
const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => i + 1);
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, i) => i);
const MINUTE_OPTIONS = Array.from({ length: 60 }, (_, i) => i);

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

export function InputScreen({ isSubmitting, errorMessage, onSubmit, onOpenHistory }: InputScreenProps) {
  const [gender, setGender] = useState<Gender>('male');
  const [calendar, setCalendar] = useState<Calendar>('solar');
  const [birthYear, setBirthYear] = useState('');
  const [birthMonth, setBirthMonth] = useState('');
  const [birthDay, setBirthDay] = useState('');
  const [isTimeUnknown, setIsTimeUnknown] = useState(false);
  const [birthHour, setBirthHour] = useState('');
  const [birthMinute, setBirthMinute] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isTakingLong, setIsTakingLong] = useState(false);

  const dayOptions = (() => {
    const year = Number(birthYear);
    const month = Number(birthMonth);
    const max = birthYear && birthMonth ? daysInMonth(year, month) : 31;
    return Array.from({ length: max }, (_, i) => i + 1);
  })();

  const clampBirthDay = (year: string, month: string) => {
    if (birthDay && year && month && Number(birthDay) > daysInMonth(Number(year), Number(month))) {
      setBirthDay('');
    }
  };

  const handleYearChange = (value: string) => {
    setBirthYear(value);
    clampBirthDay(value, birthMonth);
  };

  const handleMonthChange = (value: string) => {
    setBirthMonth(value);
    clampBirthDay(birthYear, value);
  };

  useEffect(() => {
    if (!isSubmitting) return;
    const timer = window.setTimeout(() => setIsTakingLong(true), 8000);
    return () => window.clearTimeout(timer);
  }, [isSubmitting]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!birthYear || !birthMonth || !birthDay) {
      setValidationError('생년월일을 모두 선택해주세요.');
      return;
    }
    if (!isTimeUnknown && (!birthHour || !birthMinute)) {
      setValidationError('태어난 시간을 선택하거나, 시간을 모른다면 위 체크박스를 눌러주세요.');
      return;
    }
    setValidationError(null);
    setIsTakingLong(false);

    const pad = (value: string) => value.padStart(2, '0');

    onSubmit({
      birth_date: `${birthYear}-${pad(birthMonth)}-${pad(birthDay)}`,
      birth_time: isTimeUnknown ? null : `${pad(birthHour)}:${pad(birthMinute)}:00`,
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
          <span className="field-group__label">생년월일</span>
          <div className="select-row">
            <NumberSelect
              value={birthYear}
              onChange={handleYearChange}
              options={YEAR_OPTIONS}
              placeholder="년"
              ariaLabel="태어난 연도"
              wide
            />
            <NumberSelect
              value={birthMonth}
              onChange={handleMonthChange}
              options={MONTH_OPTIONS}
              placeholder="월"
              ariaLabel="태어난 월"
            />
            <NumberSelect
              value={birthDay}
              onChange={setBirthDay}
              options={dayOptions}
              placeholder="일"
              ariaLabel="태어난 일"
            />
          </div>
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
            <span className="field-group__label">태어난 시간</span>
            <div className="select-row">
              <NumberSelect
                value={birthHour}
                onChange={setBirthHour}
                options={HOUR_OPTIONS}
                placeholder="시"
                ariaLabel="태어난 시"
                pad
              />
              <NumberSelect
                value={birthMinute}
                onChange={setBirthMinute}
                options={MINUTE_OPTIONS}
                placeholder="분"
                ariaLabel="태어난 분"
                pad
              />
            </div>
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
