// Низкоуровневый HTTP-клиент: токены, обновление сессии, ошибки

import type { Tokens } from "./types";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function hasSession(): boolean {
  return localStorage.getItem(ACCESS_KEY) !== null;
}

export function saveTokens(tokens: Tokens): void {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// Кто-то (обычно AuthProvider) узнаёт, что сессия кончилась
type Listener = () => void;
const expiredListeners = new Set<Listener>();

export function onSessionExpired(listener: Listener): () => void {
  expiredListeners.add(listener);
  return () => expiredListeners.delete(listener);
}

// Превратить ответ FastAPI с ошибкой в понятный текст
function errorMessage(status: number, data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item: { loc?: (string | number)[]; msg?: string }) => {
        const field = (item.loc ?? []).filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg}` : String(item.msg);
      })
      .join("\n");
  }

  if (typeof detail === "string") {
    return detail;
  }

  return `Ошибка ${status}`;
}

// Если несколько запросов одновременно получили 401,
// токен обновляется один раз, остальные ждут тот же результат
let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);

  if (!refreshToken) {
    return false;
  }

  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        return false;
      }

      saveTokens((await response.json()) as Tokens);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

export async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  canRetry = true,
): Promise<T> {
  const headers: Record<string, string> = {};

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const token = localStorage.getItem(ACCESS_KEY);

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;

  try {
    response = await fetch(API_URL + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, `Нет связи с сервером. Проверьте, что бэкенд запущен на ${API_URL}`);
  }

  if (response.status === 401 && canRetry && !path.startsWith("/auth/login")) {
    if (await refreshTokens()) {
      return request<T>(method, path, body, false);
    }

    clearTokens();
    expiredListeners.forEach((listener) => listener());
    throw new ApiError(401, "Сессия истекла, войдите снова");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(response.status, data));
  }

  return data as T;
}

// Собрать строку запроса, пропуская пустые значения
export function query(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }

  const text = search.toString();
  return text ? `?${text}` : "";
}
