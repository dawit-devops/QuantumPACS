import { useEffect } from "react";

export { useFetch } from "./api/useFetch";

// Sets document.title from an effect (Q-4) instead of during render, which
// React 19 treats as a side effect in the render phase.
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title;
  }, [title]);
}
