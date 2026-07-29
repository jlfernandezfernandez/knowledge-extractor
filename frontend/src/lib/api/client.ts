export const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

/** Pull the backend's `detail` out of a failed response, falling back to the
 *  status line. FastAPI always sends one; a proxy in front of it might not. */
export async function failure(response: Response): Promise<Error> {
  const body = await response.json().catch(() => ({}));
  return new Error(body.detail ?? `${response.status} ${response.statusText}`);
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: init?.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) throw await failure(response);
  return response.json();
}

export const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
