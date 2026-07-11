const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const ACCESS_COOKIE = 'koptumbuh_token';
const REFRESH_COOKIE = 'koptumbuh_refresh';
const REFRESH_STORAGE_KEY = 'koptumbuh_refresh';

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

/** Cookie flags: SameSite=Lax always; Secure only on HTTPS (already used by login). */
function cookieFlags(maxAge: number): string {
  const isSecure = typeof window !== 'undefined' && window.location.protocol === 'https:';
  return `path=/; max-age=${maxAge}; SameSite=Lax${isSecure ? '; Secure' : ''}`;
}

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function getAccessToken(): string | null {
  return readCookie(ACCESS_COOKIE);
}

export function getRefreshToken(): string | null {
  const fromCookie = readCookie(REFRESH_COOKIE);
  if (fromCookie) return fromCookie;
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem(REFRESH_STORAGE_KEY);
  }
  return null;
}

export function setTokens(access: string, refresh?: string) {
  if (typeof document === 'undefined') return;
  document.cookie = `${ACCESS_COOKIE}=${encodeURIComponent(access)}; ${cookieFlags(86400)}`;
  if (refresh) {
    document.cookie = `${REFRESH_COOKIE}=${encodeURIComponent(refresh)}; ${cookieFlags(604800)}`;
    try {
      localStorage.setItem(REFRESH_STORAGE_KEY, refresh);
    } catch {
      /* ignore quota / private mode */
    }
  }
}

export function clearTokens() {
  if (typeof document === 'undefined') return;
  document.cookie = `${ACCESS_COOKIE}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
  document.cookie = `${REFRESH_COOKIE}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
  try {
    localStorage.removeItem(REFRESH_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

function redirectToLogin() {
  clearTokens();
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function tryRefreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  // Deduplicate concurrent 401s into one refresh call
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return null;
        const json = await res.json();
        const access = json?.data?.access_token as string | undefined;
        if (!access) return null;
        setTokens(access);
        return access;
      } catch {
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit,
  _retried = false,
): Promise<{ success: boolean; data?: T; meta?: any; error?: any }> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

  if (res.status === 401) {
    const isAuthEndpoint = endpoint.startsWith('/auth/');
    if (!isAuthEndpoint && !_retried) {
      const newAccess = await tryRefreshAccessToken();
      if (newAccess) {
        return apiClient<T>(endpoint, options, true);
      }
    }
    redirectToLogin();
    throw new ApiError('UNAUTHORIZED', 'Session expired', 401);
  }

  let json: any = {};
  try {
    json = await res.json();
  } catch {
    throw new ApiError('PARSE_ERROR', 'Invalid server response', res.status);
  }

  if (!res.ok) {
    const message =
      json.error?.message ||
      (typeof json.detail === 'string' ? json.detail : null) ||
      json.detail?.[0]?.msg ||
      'Unknown error';
    throw new ApiError(json.error?.code || 'ERROR', message, res.status);
  }

  return json;
}

/** Download binary export (not JSON). Uses refresh-on-401 like apiClient. */
export async function downloadExport(id: string): Promise<void> {
  const doFetch = async (access: string | null) => {
    const headers: Record<string, string> = {};
    if (access) headers['Authorization'] = `Bearer ${access}`;
    return fetch(`${API_BASE}/admin/export/download/${id}`, { headers });
  };

  let res = await doFetch(getAccessToken());
  if (res.status === 401) {
    const newAccess = await tryRefreshAccessToken();
    if (!newAccess) {
      redirectToLogin();
      throw new ApiError('UNAUTHORIZED', 'Session expired', 401);
    }
    res = await doFetch(newAccess);
  }
  if (!res.ok) {
    throw new ApiError('DOWNLOAD_ERROR', 'Gagal mengunduh file', res.status);
  }

  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || `export_${id}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export { API_BASE };
