// Shared allow-list sanitizer for rich-text report sections (findings,
// impression, recommendations). The report editor produces a small set of
// formatting tags; anything else is flattened to text so a final report can
// never carry script/style/iframe payloads into the document or the portal.

const ALLOWED_TAGS = new Set([
  "b", "strong", "i", "em", "u", "ul", "ol", "li", "p", "br", "div",
]);

export function sanitizeReportHtml(html: string): string {
  if (!html) return "";
  if (typeof document === "undefined") return html;
  const template = document.createElement("template");
  template.innerHTML = html;
  const sanitizeNode = (node: Node): void => {
    if (node.nodeType === 3) return; // text
    if (node.nodeType === 1) {
      const el = node as HTMLElement;
      const tag = el.tagName.toLowerCase();
      if (!ALLOWED_TAGS.has(tag)) {
        const text = document.createTextNode(el.textContent || "");
        el.parentNode?.replaceChild(text, el);
        return;
      }
      // Strip every attribute (class/style/on* included) — formatting tags
      // carry no needed attributes.
      while (el.attributes.length > 0) {
        el.removeAttribute(el.attributes[0].name);
      }
      Array.from(el.childNodes).forEach(sanitizeNode);
    }
  };
  Array.from(template.content.childNodes).forEach(sanitizeNode);
  return template.innerHTML;
}

/** Flatten rich text to plain text (e.g. ORU, version diff previews). */
export function reportHtmlToText(html: string): string {
  if (!html) return "";
  if (typeof document === "undefined") return html;
  const template = document.createElement("template");
  template.innerHTML = html;
  return (template.content.textContent || "").replace(/\n{3,}/g, "\n\n").trim();
}