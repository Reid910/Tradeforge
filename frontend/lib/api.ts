const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type NodeStatus = "locked" | "discovered" | "unlocked";

export interface ResourceOut {
  key: string;
  name: string;
  icon: string;
  category: string;
  rarity: string;
  yield_amount: number;
  base_value: string;
}

export interface MapNodeOut {
  // Index signature required so this type satisfies React Flow's
  // `Node<T extends Record<string, unknown>>` constraint.
  [key: string]: unknown;
  node_key: string;
  status: NodeStatus;
  resource: ResourceOut | null;
}

export interface MapEdgeOut {
  source: string;
  target: string;
}

export interface MapResponse {
  nodes: MapNodeOut[];
  edges: MapEdgeOut[];
}

export interface UnlockResponse {
  unlocked: string;
  newly_discovered: string[];
}

export interface UserOut {
  id: number;
  username: string;
  email: string | null;
  is_guest: boolean;
  balance: string;
  created_at: string;
}

export interface MagicLinkRequestResponse {
  message: string;
  dev_magic_link: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response had no JSON body
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  requestMagicLink: (email: string) =>
    request<MagicLinkRequestResponse>("/api/auth/magic-link", { method: "POST", body: JSON.stringify({ email }) }),
  confirmMagicLink: (token: string) =>
    request<UserOut>("/api/auth/magic-link/confirm", { method: "POST", body: JSON.stringify({ token }) }),
  guestLogin: () => request<UserOut>("/api/auth/guest", { method: "POST" }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  me: () => request<UserOut>("/api/auth/me"),
  getMap: () => request<MapResponse>("/api/map"),
  unlockNode: (nodeKey: string) => request<UnlockResponse>(`/api/map/nodes/${nodeKey}/unlock`, { method: "POST" }),
};
