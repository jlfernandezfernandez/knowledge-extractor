export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly code: string;
  readonly fields?: Record<string, string>;

  constructor({ code, message, fields }: { code: string; message: string; fields?: Record<string, string> }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.fields = fields;
  }
}

function errorBody(value: unknown, response: Response) {
  if (typeof value !== "object" || value === null) {
    return { code: "request_failed", message: `${response.status} ${response.statusText}` };
  }

  const body = value as Record<string, unknown>;
  return {
    code: typeof body.code === "string" ? body.code : "request_failed",
    message: typeof body.message === "string" ? body.message : `${response.status} ${response.statusText}`,
    fields: typeof body.fields === "object" && body.fields !== null
      ? Object.fromEntries(Object.entries(body.fields).filter((entry): entry is [string, string] => typeof entry[1] === "string"))
      : undefined,
  };
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, credentials: "include", headers });
  if (!response.ok) throw new ApiError(errorBody(await response.json().catch(() => null), response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
