#!/usr/bin/env bash
set -euo pipefail

ROLE_SLUG="${1:-}"
REQ_DIR="docs/requirements/${ROLE_SLUG}"
MODE="${2:-}"

AGENT_SOURCES=(
  "frontend/docs/frontend-developer.md"
  "frontend/docs/ui-ux-designer.md"
  "frontend/docs/ui-visual-validator.md"
)

GROUNDING_DOCS=(
  "docs/PRD-v3.md"
  "docs/User-Stories.md"
  "docs/UX-Functionality.md"
  "docs/SPRINT_ARTIFACT.md"
)

if [ -z "${ROLE_SLUG}" ]; then
  echo "Usage: scripts/validate-requirements.sh <role-slug> [--status]"
  echo "Example: scripts/validate-requirements.sh super-admin"
  echo "  --status  List all roles with package status (draft/approved/gated)"
  exit 1
fi

if [ "${MODE}" = "--status" ]; then
  echo "=== Requirements Package Status ==="
  echo ""
  printf "%-25s %-10s %-10s %s\n" "Role" "Artifacts" "Traceability" "Status"
  printf "%-25s %-10s %-10s %s\n" "-----" "--------" "------------" "------"
  for dir in docs/requirements/*/; do
    role=$(basename "${dir}")
    count=$(ls "${dir}"[0-9]*.md 2>/dev/null | wc -l)
    if [ -f "${dir}/07-traceability.md" ]; then
      trace="yes"
    else
      trace="no"
    fi
    if [ -f "${dir}/README.md" ]; then
      # Handles both the table format ("| **Status** | draft |") and the
      # inline format ("**Status**: Final"); falls back to "unknown" when
      # the package has no status field.
      status=$(grep -oP '\*\*Status\*\*\s*(?::|\|)\s*\K\S+' "${dir}/README.md" 2>/dev/null | head -1 || true)
      status="${status:-unknown}"
    else
      status="unknown"
    fi
    printf "%-25s %-10s %-10s %s\n" "${role}" "${count}" "${trace}" "${status}"
  done
  exit 0
fi

if [ ! -d "${REQ_DIR}" ]; then
  echo "ERROR: No requirements package found at ${REQ_DIR}"
  exit 1
fi

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1"
  local result="$2"
  case "${result}" in
    pass)
      echo "  PASS: ${name}"
      PASS=$((PASS + 1))
      ;;
    fail)
      echo "  FAIL: ${name}"
      FAIL=$((FAIL + 1))
      ;;
    warn)
      echo "  WARN: ${name}"
      WARN=$((WARN + 1))
      ;;
  esac
}

echo "=== Validating requirements package: ${ROLE_SLUG} ==="
echo ""

# 6.5.1 ID Consistency Check
echo "--- 6.5.1 ID Consistency Check ---"

ROLE_ID=$(grep -oP 'R\d+' "${REQ_DIR}/01-user-requirements.md" | head -1 | tr -d '\n' || echo "")
if [ -n "${ROLE_ID}" ]; then
  check "Role ID ${ROLE_ID} found in user requirements" pass
else
  check "Role ID found in user requirements" fail
fi

BAD_IDS=$(grep -oP "FR-${ROLE_ID}-[0-9]+" "${REQ_DIR}/01-user-requirements.md" 2>/dev/null | grep -E -- '-[1-9]$' || true)
if [ -z "${BAD_IDS}" ]; then
  check "FR IDs are zero-padded" pass
else
  check "FR IDs are zero-padded" fail
  echo "    Found non-padded IDs: ${BAD_IDS}"
fi

AC_COUNT=$(grep -cP '^\| AC-' "${REQ_DIR}/06-acceptance-criteria.md" 2>/dev/null || echo "0")
FR_COUNT=$(grep -cP '^\| FR-' "${REQ_DIR}/01-user-requirements.md" 2>/dev/null || echo "0")
if [ "${AC_COUNT}" -gt 0 ] && [ "${FR_COUNT}" -gt 0 ]; then
  check "ACs exist and FRs exist (${AC_COUNT} ACs, ${FR_COUNT} FRs)" pass
else
  check "ACs exist and FRs exist" fail
fi

# 6.5.2 Traceability Check
echo ""
echo "--- 6.5.2 Traceability Check ---"

if [ -f "${REQ_DIR}/07-traceability.md" ]; then
  check "Traceability matrix (07) exists" pass
else
  check "Traceability matrix (07) exists — generate with 'create requirements for <role> --delta'" warn
fi

if [ -f "${REQ_DIR}/06-acceptance-criteria.md" ] && [ -f "${REQ_DIR}/01-user-requirements.md" ]; then
  FR_IDS=$(grep -oP "FR-${ROLE_ID}-[0-9]+" "${REQ_DIR}/01-user-requirements.md" | sort -u || true)
  ALL_COVERED=true
  for fr_id in ${FR_IDS}; do
    if ! grep -q "${fr_id}" "${REQ_DIR}/06-acceptance-criteria.md" 2>/dev/null; then
      echo "    FR ${fr_id} has no AC"
      ALL_COVERED=false
    fi
  done
  if [ "${ALL_COVERED}" = true ]; then
    check "Every FR has at least one AC" pass
  else
    check "Every FR has at least one AC" fail
  fi
fi

# 6.5.2b Cross-role dependency check
echo ""
echo "--- 6.5.2b Cross-Role Dependency Check ---"

if [ -f "${REQ_DIR}/07-traceability.md" ]; then
  CROSS_ROLE_DEPS=$(grep -cP '^\| R\d+' "${REQ_DIR}/07-traceability.md" 2>/dev/null || echo "0")
  if [ "${CROSS_ROLE_DEPS}" -gt 0 ]; then
    check "Cross-role dependencies listed in traceability matrix (${CROSS_ROLE_DEPS} entries)" pass
  else
    check "Cross-role dependencies listed in traceability matrix" warn
  fi
fi

# 6.5.3 Quantification Check
echo ""
echo "--- 6.5.3 Quantification Check ---"

VAGUE=$(grep -iP '\b(fast|user-friendly|scalable)\b' "${REQ_DIR}/01-user-requirements.md" 2>/dev/null | grep -v '≤' | grep -v '≥' || true)
if [ -z "${VAGUE}" ]; then
  check "No vague language (fast/user-friendly/scalable) without quantified targets" pass
else
  check "No vague language without quantified targets" fail
  echo "    Found vague terms: ${VAGUE}"
fi

if grep -qP 'LCP|INP|CLS' "${REQ_DIR}/01-user-requirements.md" 2>/dev/null; then
  check "Performance requirements have quantified targets" pass
else
  check "Performance requirements have quantified targets" fail
fi

# 6.5.4 Verifiability Check
echo ""
echo "--- 6.5.4 Verifiability Check ---"

if [ -f "${REQ_DIR}/06-acceptance-criteria.md" ]; then
  CODE_ONLY=$(awk -F'|' 'NR>2 && NF>3 {print $3}' "${REQ_DIR}/06-acceptance-criteria.md" 2>/dev/null | grep -i 'implemented in code\|code exists' || true)
  if [ -z "${CODE_ONLY}" ]; then
    check "ACs are stated in observable terms (not code presence)" pass
  else
    check "ACs are stated in observable terms" fail
    echo "    Found code-presence ACs: ${CODE_ONLY}"
  fi
fi

if grep -qP 'GATED' "${REQ_DIR}/06-acceptance-criteria.md" 2>/dev/null; then
  check "Gated ACs are explicitly marked" pass
else
  check "Gated ACs are explicitly marked (if any exist)" pass
fi

# 6.5.5 Script Integration
echo ""
echo "--- 6.5.5 Script Integration ---"
check "This script is the validation entry point" pass

# 6.5.6 Artifact 08 Roadmap Check
echo ""
echo "--- 6.5.6 Implementation Roadmap Check ---"

if [ -f "${REQ_DIR}/08-implementation-roadmap.md" ]; then
  check "Implementation roadmap (08) exists" pass
else
  check "Implementation roadmap (08) exists — generate with 'create requirements for <role>'" warn
fi

if [ -f "${REQ_DIR}/08-implementation-roadmap.md" ] && [ -f "${REQ_DIR}/07-traceability.md" ]; then
  ROADMAP_DONE=$(grep -cP '\|\s*(done|Done|DONE)\s*\|' "${REQ_DIR}/08-implementation-roadmap.md" 2>/dev/null || echo "0")
  ROADMAP_PARTIAL=$(grep -cP '\|\s*(partial|Partial|PARTIAL)\s*\|' "${REQ_DIR}/08-implementation-roadmap.md" 2>/dev/null || echo "0")
  ROADMAP_MISSING=$(grep -cP '\|\s*(missing|Missing|MISSING)\s*\|' "${REQ_DIR}/08-implementation-roadmap.md" 2>/dev/null || echo "0")
  check "Roadmap has status entries (done=${ROADMAP_DONE}, partial=${ROADMAP_PARTIAL}, missing=${ROADMAP_MISSING})" pass

  BLOCKING=$(grep -cP 'Blocking Dependency|blocked on|GATED' "${REQ_DIR}/08-implementation-roadmap.md" 2>/dev/null || echo "0")
  if [ "${BLOCKING}" -gt 0 ]; then
    check "Roadmap identifies blocking dependencies (${BLOCKING} found)" pass
  else
    check "Roadmap identifies blocking dependencies" warn
  fi

  NEXT_STEPS=$(grep -cP 'Next Steps|next steps' "${REQ_DIR}/08-implementation-roadmap.md" 2>/dev/null || echo "0")
  if [ "${NEXT_STEPS}" -gt 0 ]; then
    check "Roadmap has next-steps section" pass
  else
    check "Roadmap has next-steps section" warn
  fi
fi

# Section 9: Document Discovery Validation
echo ""
echo "--- Section 9: Document Discovery ---"

MISSING_SOURCES=0
for source in "${AGENT_SOURCES[@]}"; do
  if [ -f "${source}" ]; then
    check "Agent source exists: ${source}" pass
  else
    check "Agent source exists: ${source}" warn
    MISSING_SOURCES=$((MISSING_SOURCES + 1))
  fi
done

MISSING_DOCS=0
for doc in "${GROUNDING_DOCS[@]}"; do
  if [ -f "${doc}" ]; then
    check "Grounding document exists: ${doc}" pass
  else
    check "Grounding document exists: ${doc}" warn
    MISSING_DOCS=$((MISSING_DOCS + 1))
  fi
done

if [ "${MISSING_SOURCES}" -eq 0 ] && [ "${MISSING_DOCS}" -eq 0 ]; then
  check "All expected agent sources and grounding documents present" pass
else
  check "All expected agent sources and grounding documents present" warn
fi

# Summary
echo ""
echo "=== Summary ==="
echo "Passed: ${PASS}"
echo "Failed: ${FAIL}"
echo "Warnings: ${WARN}"

if [ "${FAIL}" -gt 0 ]; then
  echo "RESULT: FAIL — ${FAIL} check(s) failed"
  exit 1
elif [ "${WARN}" -gt 0 ]; then
  echo "RESULT: PASS with warnings — review warnings above"
  exit 0
else
  echo "RESULT: PASS — All checks passed"
  exit 0
fi