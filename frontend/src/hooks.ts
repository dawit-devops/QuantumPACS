import { useState, useEffect, useRef } from "react";

export { useFetch } from "./api/useFetch";

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
    },
  };
}

export function usePrevious(value: any) {
  const ref = useRef<any>(null);
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}

// Sets document.title from an effect (Q-4) instead of during render, which
// React 19 treats as a side effect in the render phase.
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title;
  }, [title]);
}
