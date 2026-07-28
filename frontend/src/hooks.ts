import { useState, useEffect, useRef } from 'react';
import { LOADING_DELAY, API_URL } from './config';
import { handleResponse, getAccessToken, getRefreshToken, setTokens, tryRefreshToken } from './helpers';
import { navigate } from './navigator';

async function fetchWithRetry(url: string, options: any, retries = 3): Promise<Response> {
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

function addAuthHeader(headers: Headers): void {
  const token = getAccessToken();
  if (token) {
    headers.set('X-Auth-Pacs', token);
  }
}

export function useFetch(url: string, options: any = {}) {
  const [loading, setLoading] = useState(false);
  const [showLoading, setShowLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<any>(null);
  const controller = useRef<AbortController | null>(null);

  if (!url.startsWith('http')) {
    url = `${API_URL}/${url}`;
  }
  const exec = async (doShowLoading = true, execOptions: any = {}): Promise<void> => {
    if (controller.current) {
      controller.current.abort();
    }
    setLoading(true);
    let loaderTimeout: ReturnType<typeof setTimeout> | undefined;
    if (doShowLoading) {
      loaderTimeout = setTimeout(
        () => setShowLoading(true),
        LOADING_DELAY,
      );
    }
    const finish = () => {
      if (doShowLoading) {
        clearTimeout(loaderTimeout);
        setShowLoading(false);
      }
      setLoading(false);
    };

    options.headers = new Headers({
      'Content-Type': 'application/json',
    });
    addAuthHeader(options.headers);
    controller.current = new AbortController();
    options.signal = controller.current.signal;

    const doFetch = async (): Promise<any> => {
      const resp = await fetchWithRetry(url, Object.assign({}, options, execOptions));
      return await handleResponse(resp);
    };

    try {
      const result = await doFetch();
      setData(result);
      finish();
    }
    catch (error: any) {
      if (error.error === 401) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
          addAuthHeader(options.headers);
          try {
            const result = await doFetch();
            setData(result);
            finish();
            return;
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
        setError(error.error || error.message || error);
      }
      finish();
    }
  };
  return {exec, loading, showLoading, data, error, controller};
}

export function useFormInput(initalState: string) {
  const [value, setValue] = useState(initalState);

  return {
    value: value,
    onChange: (e: any) => {
      if (e.target) {
        setValue(e.target.value);
      } else {
        setValue(e);
      }
    }
  };
}

export function usePrevious(value: any) {
  const ref = useRef<any>(null);
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}
