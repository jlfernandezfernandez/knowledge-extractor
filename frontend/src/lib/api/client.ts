import { api, API_URL, ApiError } from "@/lib/api";

export { API_URL };

/** Pull the backend's `detail` out of a failed response, falling back to the
 *  status line. FastAPI always sends one; a proxy in front of it might not. */
export async function failure(response: Response): Promise<Error> {
  const body = await response.json().catch(() => ({}));
  return new ApiError({
    code: typeof body.code === "string" ? body.code : "request_failed",
    message: typeof body.message === "string" ? body.message : body.detail ?? `${response.status} ${response.statusText}`,
  });
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return api<T>(path, init);
}

export const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
