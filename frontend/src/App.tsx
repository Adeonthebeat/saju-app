import { useEffect, useState } from 'react';
import { analyzeSaju, type SajuAnalyzeRequest, type SajuAnalyzeResponse, type SajuHistoryItem } from './api/saju';
import { getUserKey } from './api/user';
import { HistoryScreen } from './pages/HistoryScreen';
import { InputScreen } from './pages/InputScreen';
import { ResultScreen } from './pages/ResultScreen';

type Screen =
  | { type: 'input' }
  | { type: 'result'; data: SajuAnalyzeResponse }
  | { type: 'history' }
  | { type: 'historyDetail'; data: SajuHistoryItem };

const ROOT_SCREEN: Screen = { type: 'input' };

function App() {
  const [stack, setStack] = useState<Screen[]>([ROOT_SCREEN]);
  const [userKey, setUserKey] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    getUserKey().then(setUserKey);
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setStack((current) => (current.length > 1 ? current.slice(0, -1) : current));
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const push = (screen: Screen) => {
    window.history.pushState({ depth: stack.length + 1 }, '');
    setStack((current) => [...current, screen]);
  };

  const goBack = () => {
    window.history.back();
  };

  const handleSubmit = async (payload: Omit<SajuAnalyzeRequest, 'user_key'>) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const response = await analyzeSaju({ ...payload, user_key: userKey });
      push({ type: 'result', data: response });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '알 수 없는 오류가 발생했어요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const current = stack[stack.length - 1];

  if (current.type === 'result') {
    return <ResultScreen result={current.data} onRestart={goBack} />;
  }

  if (current.type === 'historyDetail') {
    return <ResultScreen result={current.data} onRestart={goBack} restartLabel="목록으로" />;
  }

  if (current.type === 'history') {
    // userKey가 없으면 애초에 history 화면으로 push되지 않으므로 항상 존재한다.
    return <HistoryScreen userKey={userKey!} onSelect={(item) => push({ type: 'historyDetail', data: item })} />;
  }

  return (
    <InputScreen
      isSubmitting={isSubmitting}
      errorMessage={errorMessage}
      onSubmit={handleSubmit}
      onOpenHistory={userKey ? () => push({ type: 'history' }) : undefined}
    />
  );
}

export default App;
