"""Nursing surfaces substrate + G3 coordinator grants (§2.11)

Revision ID: 100
Revises: 099
Create Date: 2026-08-25

Why
---
Migration 037 (R11 Nursing) created the nursing tables but nothing ever
consumed them: no API layer, no UI, and the NURSING_READ/NURSING_WRITE
grants were held by no role after 052 deleted the legacy `nurse` slug.
Round 5 of the ui-ux-redesign-spec review builds §2.11 (N-01..N-04) on this
substrate. G3 (human-approved 2026-08-25): care_coordinator becomes the
grant holder, formalizing 052's nurse→care_coordinator remap.

Schema
------
* `vitals` gains weight/height (spec N-01) plus the tenant_id tag column —
  pool isolation stays authoritative; the tag follows the encounters/
  care_plans convention so rows are attributable in shared dev databases.
* `prep_checklists` gets the same tenant_id tag.
* New `contrast_consents` (N-03: digital contrast consent with signature,
  kiosk-consent shape) and `exam_notes` (N-04: attributed exam-scoped notes).
* G3 grant append to the built-in care_coordinator role + token_version bump
  (061 pattern; JWTs embed permissions at login).

Rollback
--------
Drops the two new tables and removes both grants (bumping token_version
again). The additive vitals/prep_checklists columns stay — they carry no
data until the feature is used and dropping them risks losing recorded
vitals on downgrade.
"""

import json

from alembic import op
from sqlalchemy import text

revision = '100'
down_revision = '099'
branch_labels = None
depends_on = None

GRANTS = ('NURSING_READ', 'NURSING_WRITE')

_DDL = (
    # N-01: spec asks for weight/height alongside the 037 vitals columns.
    ("ALTER TABLE vitals ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(5, 1)"),
    ("ALTER TABLE vitals ADD COLUMN IF NOT EXISTS height_cm NUMERIC(5, 1)"),
    # Tenant tag columns on the used 037 tables (pool+tag convention).
    (
        "ALTER TABLE vitals ADD COLUMN IF NOT EXISTS tenant_id "
        "TEXT NOT NULL DEFAULT 'default'"
    ),
    (
        "ALTER TABLE prep_checklists ADD COLUMN IF NOT EXISTS tenant_id "
        "TEXT NOT NULL DEFAULT 'default'"
    ),
    "CREATE INDEX IF NOT EXISTS ix_vitals_exam ON vitals(exam_id)",
    (
        "CREATE INDEX IF NOT EXISTS ix_prep_checklists_exam "
        "ON prep_checklists(exam_id)"
    ),
    # N-03: digital contrast consent (kiosk consent shape).
    ("""
    CREATE TABLE IF NOT EXISTS contrast_consents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID,
        patient_id TEXT NOT NULL,
        consent_text_version TEXT DEFAULT '',
        accepted BOOLEAN NOT NULL DEFAULT TRUE,
        signature_png TEXT DEFAULT '',
        declined_reason TEXT DEFAULT '',
        witnessed_by TEXT DEFAULT '',
        signed_by TEXT DEFAULT '',
        signed_at TIMESTAMPTZ DEFAULT now(),
        created_at TIMESTAMPTZ DEFAULT now(),
        tenant_id TEXT NOT NULL DEFAULT 'default'
    )
    """),
    (
        "CREATE INDEX IF NOT EXISTS ix_contrast_consents_exam "
        "ON contrast_consents(tenant_id, exam_id, signed_at DESC)"
    ),
    # N-04: attributed exam-scoped notes visible to tech + radiologist.
    ("""
    CREATE TABLE IF NOT EXISTS exam_notes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        exam_id UUID,
        patient_id TEXT NOT NULL,
        note TEXT NOT NULL,
        author_id TEXT DEFAULT '',
        author_role TEXT DEFAULT 'nurse',
        created_at TIMESTAMPTZ DEFAULT now(),
        tenant_id TEXT NOT NULL DEFAULT 'default'
    )
    """),
    (
        "CREATE INDEX IF NOT EXISTS ix_exam_notes_exam "
        "ON exam_notes(tenant_id, exam_id, created_at DESC)"
    ),
)


def _coordinator_roles(conn):
    return conn.execute(
        text("SELECT id, permissions FROM roles WHERE slug = 'care_coordinator'")
    ).fetchall()


def _patch_grants(conn, add):
    changed = False
    for role_id, permissions in _coordinator_roles(conn):
        perms = json.loads(permissions) if isinstance(permissions, str) else list(permissions or [])
        new_perms = list(perms)
        for grant in GRANTS:
            if add and grant not in new_perms:
                new_perms.append(grant)
            elif not add and grant in new_perms:
                new_perms.remove(grant)
        if new_perms != perms:
            conn.execute(
                text(
                    "UPDATE roles SET permissions = :permissions, "
                    "updated_at = now() WHERE id = :role_id"
                ),
                {'permissions': json.dumps(new_perms), 'role_id': role_id},
            )
            changed = True
    return changed


def _bump_token_version(conn):
    conn.execute(
        text(
            """
            UPDATE users
            SET token_version = token_version + 1
            WHERE role_id IN (SELECT id FROM roles WHERE slug = 'care_coordinator')
            """
        )
    )


def upgrade():
    conn = op.get_bind()
    for stmt in _DDL:
        op.execute(stmt)
    if _patch_grants(conn, add=True):
        _bump_token_version(conn)


def downgrade():
    conn = op.get_bind()
    op.execute("DROP TABLE IF EXISTS exam_notes")
    op.execute("DROP TABLE IF EXISTS contrast_consents")
    if _patch_grants(conn, add=False):
        _bump_token_version(conn)
