import React from 'react';

interface Props {
  size?: number;
  showText?: boolean;
}

const QP_GRADIENT_ID = 'quantum-logo-grad';

function QuantumLogo({ size = 40, showText = true }: Props) {
  return (
    <svg width={showText ? size + 120 : size} height={size} viewBox="0 0 180 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id={QP_GRADIENT_ID} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0077B6" />
          <stop offset="50%" stopColor="#6366F1" />
          <stop offset="100%" stopColor="#06B6D4" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="18" stroke={`url(#${QP_GRADIENT_ID})`} strokeWidth="3" fill="none" />
      <circle cx="20" cy="20" r="10" stroke="#6366F1" strokeWidth="2" fill="none" opacity="0.5" />
      <line x1="20" y1="2" x2="20" y2="10" stroke={`url(#${QP_GRADIENT_ID})`} strokeWidth="2" strokeLinecap="round" />
      <line x1="20" y1="30" x2="20" y2="38" stroke={`url(#${QP_GRADIENT_ID})`} strokeWidth="2" strokeLinecap="round" />
      <ellipse cx="20" cy="20" rx="6" ry="2.5" stroke="#06B6D4" strokeWidth="1.5" fill="none" opacity="0.6" />
      <circle cx="20" cy="20" r="2.5" fill={`url(#${QP_GRADIENT_ID})`} />
      {showText && (
        <text x="44" y="26" fontFamily="system-ui, -apple-system, sans-serif" fontSize="16" fontWeight="700" fill="#1E293B">
          Quantum<tspan fill="#6366F1">PACS</tspan>
        </text>
      )}
    </svg>
  );
}

export default QuantumLogo;
