import { useCallback, useEffect, useRef, useState } from "react";

// §5.2 keyboard map. Guard identical to the console's [ / ] handler: never
// steal keys inside inputs, content-editables, or antd overlays/dialogs.
function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  const isInput = el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable;
  const inOverlay = !!document.activeElement?.closest(
    ".ant-select, .ant-drawer, .ant-collapse, [role='dialog'], [role='menu']"
  );
  return isInput || inOverlay;
}

const STORAGE_KEY = "reading-immersive";

export interface ReaderShortcutHandlers {
  saveDraft: () => void;
  requestSign: () => void;
  submitReport: () => void;
  goPrevExam: () => void;
  goNextExam: () => void;
  goToWorklist: () => void;
  showHelp: () => void;
}

/**
 * §5 immersive reader mode + the §5.2 shortcut map.
 *
 * Immersive state persists per browser (localStorage); when the user has
 * never chosen, screens wider than 1920px (dual-monitor detection, §5.1)
 * auto-enter. The body.immersive-reading flag drives the global dark /
 * 48px-sidebar-strip styling because the sidebar renders OUTSIDE this
 * page's tree.
 *
 * Arrow keys navigate the reading QUEUE only while immersive — outside
 * immersive they keep their existing viewer binding (series file paging),
 * so enabling immersive never silently removes an interaction clinicians
 * already rely on.
 */
export function useReaderShortcuts(handlers: ReaderShortcutHandlers) {
  const [immersive, setImmersive] = useState<boolean>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) return stored === "1";
    return typeof window !== "undefined" && window.innerWidth > 1920;
  });

  const toggleImmersive = useCallback(() => {
    setImmersive((prev) => {
      localStorage.setItem(STORAGE_KEY, prev ? "0" : "1");
      return !prev;
    });
  }, []);

  // Latest-handler refs keep the single keydown binding stale-free.
  const handlersRef = useRef(handlers);
  useEffect(() => {
    handlersRef.current = handlers;
  });
  const immersiveRef = useRef(immersive);
  useEffect(() => {
    immersiveRef.current = immersive;
  }, [immersive]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      const mod = e.ctrlKey || e.metaKey;
      const key = e.key.toLowerCase();
      if (e.key === "F1") {
        e.preventDefault();
        handlersRef.current.showHelp();
      } else if (mod && e.shiftKey && key === "s") {
        // Must be tested before plain Ctrl+S.
        e.preventDefault();
        handlersRef.current.submitReport();
      } else if (mod && !e.shiftKey && key === "s") {
        e.preventDefault();
        handlersRef.current.saveDraft();
      } else if (mod && e.key === "Enter") {
        // Sign opens its confirmation modal — a finalizing action stays
        // behind an explicit confirm even at keyboard speed.
        e.preventDefault();
        handlersRef.current.requestSign();
      } else if (mod && e.shiftKey && key === "w") {
        e.preventDefault();
        handlersRef.current.goToWorklist();
      } else if (immersiveRef.current && e.key === "ArrowLeft") {
        e.preventDefault();
        handlersRef.current.goPrevExam();
      } else if (immersiveRef.current && e.key === "ArrowRight") {
        e.preventDefault();
        handlersRef.current.goNextExam();
      } else if (e.key === " ") {
        e.preventDefault();
        toggleImmersive();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [toggleImmersive]);

  useEffect(() => {
    document.body.classList.toggle("immersive-reading", immersive);
    return () => document.body.classList.remove("immersive-reading");
  }, [immersive]);

  return { immersive, toggleImmersive };
}
