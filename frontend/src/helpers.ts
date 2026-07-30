import { API_URL } from './config';
import { navigate } from './navigator';

export const handleResponse = async (response: Response): Promise<any> => {
  if (!response) {
    return;
  }
  if (!response.ok && response.status !== 400) {
    const error = {error: response.status};
    throw error;
  }
  const json = await response.json();
  if (response.ok) {
    return json;
  } else {
    const error = {error: json};
    throw error;
  }
};

interface RequestOptions {
  method?: string;
  body?: string;
  headers?: Headers;
  data?: any;
  query?: Record<string, string>;
  unauthorized?: () => void;
  [key: string]: any;
}

async function fetchWithRetry(url: string, options: RequestOptions, retries = 3): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    const resp = await fetch(url, options);
    if (resp.ok || resp.status < 500) {
      return resp;
    }
    if (i < retries - 1) {
      await new Promise(r => setTimeout(r, Math.min(1000 * Math.pow(2, i), 8000)));
    }
  }
  return fetch(url, options);
}

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token');
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token');
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

export function clearTokens(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

let refreshTimer: ReturnType<typeof setInterval> | null = null;

export function startRefreshTimer(onRefreshFailed: () => void): void {
  stopRefreshTimer();
  refreshTimer = setInterval(async () => {
    const token = getAccessToken();
    if (!token) return;
    const ok = await tryRefreshToken();
    if (!ok) {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        const payload = refreshToken.split('.')[1];
        try {
          const decoded = JSON.parse(atob(payload));
          if (decoded.exp * 1000 < Date.now()) {
            onRefreshFailed();
          }
        } catch {}
      }
    }
  }, 25 * 60 * 1000);
}

export function stopRefreshTimer(): void {
  if (refreshTimer !== null) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

export async function tryRefreshToken(): Promise<boolean> {
  const token = getRefreshToken();
  if (!token) return false;
  try {
    const resp = await fetch(`${API_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: token }),
    });
    if (!resp.ok) return false;
    const data = await resp.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export const request = async (url: string, options: RequestOptions = {}): Promise<any> => {
  if (!url.startsWith('http')) {
    url = `${API_URL}/${url}`;
  }
  options.headers = new Headers({
    'Content-Type': 'application/json',
  });
  const token = getAccessToken();
  if (token) {
    options.headers.set('X-Auth-Pacs', token);
  }
  if (options.data) {
    options.method = 'POST';
    options.body = JSON.stringify(options.data);
    delete options.data;
  }
  if (options.query) {
    url = `${url}?${encodeQuery(options.query)}`;
    delete options.query;
  }
  const exec = async (): Promise<any> => {
    const resp = await fetchWithRetry(url, options);
    return await handleResponse(resp);
  };
  try {
    return await exec();
  } catch (error: any) {
    if (error.error === 401) {
      const tempKey = localStorage.getItem('tempKey');
      if (tempKey) {
        sessionStorage.setItem('shareKeyError', 'expired');
      }
      const refreshed = await tryRefreshToken();
      if (refreshed) {
        const newToken = getAccessToken();
        if (newToken) {
          options.headers.set('X-Auth-Pacs', newToken);
        }
        try {
          return await exec();
        } catch {
        }
      }
      if (options.unauthorized) {
        options.unauthorized();
      } else {
        navigate('/login');
      }
    }
    if (!error.code || error.code !== 20) {
      throw Error(error.error || error.message || error);
    }
  }
};

export const open = async (url: string): Promise<void> => {
  return await request('files/download_token').then(data => {
    const token = data.token;
    if (url.includes('?')) {
      url = `${API_URL}/${url}&token=${token}`;
    } else {
      url = `${API_URL}/${url}?token=${token}`;
    }
    window.open(url);
  });
};

export const parseParams = (search: string): Record<string, string> => {
  search = search.slice(1);
  let parts = search.split('&');
  let params: Record<string, string> = {};
  for (let part of parts) {
    let [name, value] = part.split('=');
    if (name) params[name] = value;
  }
  return params;
};

export const encodeQuery = (data: Record<string, string>): string => {
  let ret: string[] = [];
  for (let d in data) {
    ret.push(encodeURIComponent(d) + '=' + encodeURIComponent(data[d]));
  }
  return ret.join('&');
};

export const updateQuery = (history: any, data: Record<string, string>): void => {
  let {pathname, search} = history.location;
  let params = parseParams(search);
  for (let k in data) {
    params[k] = data[k];
  }
  history.push(`${pathname}?${encodeQuery(params)}`);
};

export const emit = (event: string, data?: any): void => {
  let e = new CustomEvent(event, { detail: data });
  document.body.dispatchEvent(e);
};

export const subscribe = (event: string, listener: EventListener): void => {
  document.body.addEventListener(event, listener);
};

export const isAdmin = (): boolean => {
  return localStorage.getItem('admin') === 'true';
};
