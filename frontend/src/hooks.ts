import { useState, useEffect, useRef } from 'react';
import { LOADING_DELAY, API_URL } from './config';
import { handleResponse } from './helpers';
import { navigate } from './navigator';

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
      'X-Auth-Pacs': localStorage.getItem('token') || '',
      'Content-Type': 'application/json',
    });
    controller.current = new AbortController();
    options.signal = controller.current.signal;
    try {
      const resp = await fetch(url, Object.assign({}, options, execOptions));
      const data = await handleResponse(resp);
      setData(data);
      finish();
    }
    catch (error: any) {
      if (error.error === 401) {
        if (options.unauthorized) {
          options.unauthorized();
        }
        else {
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
