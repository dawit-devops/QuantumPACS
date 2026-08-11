import React from "react";

interface Props {
  size?: number;
  showText?: boolean;
}

const QP_GRADIENT_ID = "quantum-logo-grad";

function QuantumLogo({ size = 40, showText = true }: Props) {
  return (
    <svg
      width={showText ? size + 120 : size}
      height={size}
      viewBox="0 0 180 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <style>{`
        .q-stop-1 { stop-color: var(--color-blue-600); }
        .q-stop-2 { stop-color: var(--color-secondary); }
        .q-stop-3 { stop-color: var(--color-accent); }
        .q-fill-secondary { fill: var(--color-secondary); }
        .q-fill-accent { fill: var(--color-accent); }
        /* The wordmark sits on the dark sidebar (slate-900 in BOTH themes),
           so --text-primary is wrong: slate-800 in light mode is near-black
           on black. --sidebar-text is slate-300 in both themes — ~10:1. */
        .q-fill-text { fill: var(--sidebar-text); }
      `}</style>
      <defs>
        <linearGradient id={QP_GRADIENT_ID} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" className="q-stop-1" />
          <stop offset="50%" className="q-stop-2" />
          <stop offset="100%" className="q-stop-3" />
        </linearGradient>
      </defs>
      <circle
        cx="20"
        cy="20"
        r="18"
        stroke={`url(#${QP_GRADIENT_ID})`}
        strokeWidth="3"
        fill="none"
      />
      <circle
        cx="20"
        cy="20"
        r="10"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        opacity="0.5"
        className="q-fill-secondary"
      />
      <line
        x1="20"
        y1="2"
        x2="20"
        y2="10"
        stroke={`url(#${QP_GRADIENT_ID})`}
        strokeWidth="2"
        strokeLinecap="round"
      />
      <line
        x1="20"
        y1="30"
        x2="20"
        y2="38"
        stroke={`url(#${QP_GRADIENT_ID})`}
        strokeWidth="2"
        strokeLinecap="round"
      />
      <ellipse
        cx="20"
        cy="20"
        rx="6"
        ry="2.5"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        opacity="0.6"
        className="q-fill-accent"
      />
      <circle cx="20" cy="20" r="2.5" fill={`url(#${QP_GRADIENT_ID})`} />
      {showText && (
        <text
          x="44"
          y="26"
          fontFamily="system-ui, -apple-system, sans-serif"
          fontSize="16"
          fontWeight="700"
          className="q-fill-text"
        >
          Quantum<tspan className="q-fill-secondary">PACS</tspan>
        </text>
      )}
    </svg>
  );
}

export default QuantumLogo;
