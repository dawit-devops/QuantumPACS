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

export const request = async (url: string, options: RequestOptions = {}): Promise<any> => {
  if (!url.startsWith('http')) {
    url = `${API_URL}/${url}`;
  }
  options.headers = new Headers({
    'Content-Type': 'application/json',
  });
  if (options.data) {
    options.method = 'POST';
    options.body = JSON.stringify(options.data);
    delete options.data;
  }
  if (options.query) {
    url = `${url}?${encodeQuery(options.query)}`;
    delete options.query;
  }
  try {
    const resp = await fetchWithRetry(url, options);
    return await handleResponse(resp);
  } catch (error: any) {
    if (error.error === 401) {
      if (options.unauthorized) {
        options.unauthorized();
      }
      else {
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
