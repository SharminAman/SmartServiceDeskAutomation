export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized: (() => void) | null = null;

export function setUnauthorized(handler: () => void) {
  onUnauthorized = handler;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) {
    if (response.status === 401 && !path.includes("/auth/login")) onUnauthorized?.();
    let message = "Something went wrong";
    if (body && typeof body.detail === "string") message = body.detail;
    else if (body && Array.isArray(body.detail)) {
      message = body.detail.map((item: { msg?: string }) => item.msg || "Check the form").join(" ");
    }
    throw new ApiError(response.status, message);
  }
  return body as T;
}

export async function downloadCsv(scope: "all" | "view", params?: URLSearchParams) {
  const query = new URLSearchParams(params);
  query.set("scope", scope);
  if (scope === "all") {
    ["review", "missing", "match", "category", "priority", "status", "channel", "q", "open"].forEach((key) =>
      query.delete(key),
    );
  }
  const response = await fetch(`/api/requests/export?${query.toString()}`, { credentials: "include" });
  if (response.status === 401) {
    onUnauthorized?.();
    throw new ApiError(401, "Sign in to continue");
  }
  if (!response.ok) throw new ApiError(response.status, "The download did not start");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = scope === "all" ? "request-desk-all.csv" : "request-desk-view.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
