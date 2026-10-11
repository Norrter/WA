import { useCallback, useEffect, useRef, useState } from "react";

interface AsyncState<T> {
  data: T | undefined;
  error: Error | null;
  loading: boolean;
  // Загрузить заново (например, после изменения данных)
  reload: () => Promise<void>;
  // Поменять данные локально, без запроса
  setData: (data: T) => void;
}

// Загрузка данных с сервера при открытии экрана и при смене deps
export function useAsync<T>(load: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  // Ответ на устаревший запрос не должен перезаписать новый
  const requestId = useRef(0);

  const reload = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);

    try {
      const result = await load();

      if (id === requestId.current) {
        setData(result);
        setError(null);
      }
    } catch (caught) {
      if (id === requestId.current) {
        setError(caught as Error);
      }
    } finally {
      if (id === requestId.current) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, loading, reload, setData };
}
