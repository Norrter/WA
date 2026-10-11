// Всплывающие сообщения внизу экрана

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

interface ToastItem {
  id: number;
  text: string;
  error: boolean;
}

interface ToastApi {
  success: (text: string) => void;
  error: (error: unknown) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const push = useCallback((text: string, error: boolean) => {
    const id = nextId.current++;
    setItems((current) => [...current.slice(-2), { id, text, error }]);
    setTimeout(
      () => setItems((current) => current.filter((item) => item.id !== id)),
      error ? 6000 : 2800,
    );
  }, []);

  const api = useRef<ToastApi>({
    success: (text) => push(text, false),
    error: (error) =>
      push(error instanceof Error ? error.message : String(error), true),
  });

  return (
    <ToastContext.Provider value={api.current}>
      {children}
      <div className="toasts" aria-live="polite">
        {items.map((item) => (
          <div key={item.id} className={`toast ${item.error ? "toast-error" : ""}`}>
            {item.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast должен вызываться внутри ToastProvider");
  }

  return context;
}
