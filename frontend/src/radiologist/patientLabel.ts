// PHI-minimizing patient column labels: initials + MRN last-4 instead of the
// full name in queues (R13 / staff worklist). Full name stays available via
// tooltip; initials fall back to the first name when no last name is present.
export function patientInitials(name: string): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function mrnLast4(patientId: string): string {
  const id = String(patientId || "");
  return id.length > 4 ? id.slice(-4) : id;
}
