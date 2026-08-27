import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  UnorderedListOutlined,
  OrderedListOutlined,
  ClearOutlined,
} from "@ant-design/icons";
import { sanitizeReportHtml } from "./sanitizeReportHtml";
import "./RichTextEditor.css";

interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  readOnly?: boolean;
  status?: "warning" | "error" | "";
  minHeight?: number;
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = "",
  readOnly = false,
  status,
  minHeight = 80,
}: RichTextEditorProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [focused, setFocused] = useState(false);
  const cleanRef = useRef(false);
  const skipNext = useRef(false);

  const exec = useCallback(
    (cmd: string, val?: string) => {
      document.execCommand(cmd, false, val);
      if (ref.current) {
        cleanRef.current = true;
        onChange(sanitizeReportHtml(ref.current.innerHTML));
      }
    },
    [onChange]
  );

  useEffect(() => {
    if (!ref.current || skipNext.current) {
      skipNext.current = false;
      return;
    }
    if (ref.current.innerHTML !== value) {
      ref.current.innerHTML = value || "";
    }
  }, [value]);

  const onInput = useCallback(() => {
    if (ref.current && ref.current.innerHTML !== value) {
      cleanRef.current = true;
      onChange(sanitizeReportHtml(ref.current.innerHTML));
    }
  }, [onChange, value]);

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const handler = (e: Event) => {
      e.preventDefault();
      e.stopPropagation();
      const text = (e as ClipboardEvent).clipboardData?.getData("text/plain") || "";
      document.execCommand("insertText", false, text);
    };
    el.addEventListener("paste", handler);
    return () => el.removeEventListener("paste", handler);
  }, []);

  const showPlaceholder = !value || value === "<br>" || value === "";

  return (
    <div
      className={`rte-wrapper${readOnly ? " rte-readonly" : ""}${status === "warning" ? " rte-warning" : ""}`}
    >
      {" "}
      {!readOnly && (
        <div className="rte-toolbar" role="toolbar" aria-label="Text formatting">
          <button
            type="button"
            className="rte-btn"
            onClick={() => exec("bold")}
            title="Bold"
            aria-label="Bold"
          >
            <BoldOutlined />
          </button>
          <button
            type="button"
            className="rte-btn"
            onClick={() => exec("italic")}
            title="Italic"
            aria-label="Italic"
          >
            <ItalicOutlined />
          </button>
          <button
            type="button"
            className="rte-btn"
            onClick={() => exec("underline")}
            title="Underline"
            aria-label="Underline"
          >
            <UnderlineOutlined />
          </button>
          <span className="rte-sep" />
          <button
            type="button"
            className="rte-btn"
            onClick={() => exec("insertUnorderedList")}
            title="Bullet list"
            aria-label="Bullet list"
          >
            <UnorderedListOutlined />
          </button>
          <button
            type="button"
            className="rte-btn"
            onClick={() => exec("insertOrderedList")}
            title="Numbered list"
            aria-label="Numbered list"
          >
            <OrderedListOutlined />
          </button>
          <span className="rte-sep" />
          <button
            type="button"
            className="rte-btn"
            onClick={() => {
              exec("removeFormat");
              exec("undo");
            }}
            title="Clear formatting"
            aria-label="Clear formatting"
          >
            <ClearOutlined />
          </button>
        </div>
      )}
      <div
        ref={ref}
        className={`rte-editor${focused ? " rte-focused" : ""}`}
        contentEditable={!readOnly}
        onInput={onInput}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        data-placeholder={placeholder}
        role="textbox"
        aria-multiline="true"
        aria-placeholder={placeholder}
        style={{ minHeight }}
        suppressContentEditableWarning
      />
    </div>
  );
}
