export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function parseApiError(text: string, fallback: string): string {
  try {
    const data = JSON.parse(text);
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.detail === "object" && data.detail !== null) {
      return "请求参数有误，请检查后重试";
    }
  } catch {
    // keep fallback for non-JSON error bodies
  }
  return fallback;
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(parseApiError(text, `请求失败（${res.status}）`));
  }
  return res.json() as Promise<T>;
}
