"""limit notify_event() payload for files rows (LO-01, NOTIFY 8KB limit)

Revision ID: 053
Revises: 052
Create Date: 2026-08-11

Why
---
The installed notify_event() trigger forwards row_to_json(NEW) verbatim for
every table. files.meta (JSONB of all non-binary DICOM tags) routinely exceeds
PostgreSQL's 8000-byte NOTIFY payload limit for real studies (~250+ tags ≈ 10KB
JSON), so every file INSERT/UPDATE raises `payload string too long` and DICOM
uploads 500. The minimal routing-key payload for files already exists in
db/replica.py (LO-01) but only runs at DB init — existing databases never
received it. This migration applies the same function body to running DBs.

Schema
------
No table changes; CREATE OR REPLACE FUNCTION only. Consumers of the bridge
(ingestion, replica sync) only read the routing keys included below, so the
reduced payload is wire-compatible.

Rollback
--------
Restores the previous full-row function body (files rows will hit the NOTIFY
payload limit again on large metadata).
"""

from alembic import op

revision = '053'
down_revision = '052'
branch_labels = None
depends_on = None

# Keep in sync with db/replica.py: the files branch forwards only the routing
# keys the bridge needs — never the full row with its PHI-bearing meta JSONB.
_FUNCTION = """
CREATE OR REPLACE FUNCTION notify_event() RETURNS TRIGGER AS $$
  DECLARE
    record RECORD;
    payload JSON;
  BEGIN
    IF (TG_OP = 'DELETE') THEN
      record = OLD;
    ELSE
      record = NEW;
    END IF;

    IF (TG_TABLE_NAME = 'files') THEN
      payload = json_build_object(
        'table', TG_TABLE_NAME,
        'action', TG_OP,
        'old', CASE WHEN TG_OP = 'INSERT' THEN '{}'::json
                    ELSE json_build_object('id', OLD.id, 'name', OLD.name,
                                           'hash', OLD.hash,
                                           'patient_id', OLD.patient_id,
                                           'study_id', OLD.study_id,
                                           'series_id', OLD.series_id) END,
        'new', CASE WHEN TG_OP = 'DELETE' THEN '{}'::json
                    ELSE json_build_object('id', NEW.id, 'name', NEW.name,
                                           'hash', NEW.hash,
                                           'patient_id', NEW.patient_id,
                                           'study_id', NEW.study_id,
                                           'series_id', NEW.series_id) END);
    ELSE
      payload = json_build_object('table', TG_TABLE_NAME,
                                  'action', TG_OP,
                                  'old', COALESCE(row_to_json(OLD), '{}'::json),
                                  'new', COALESCE(row_to_json(NEW), '{}'::json));
    END IF;

    PERFORM pg_notify('events', payload::text);

    RETURN NULL;
  END;
  $$ LANGUAGE plpgsql;
"""

# Previous full-row body (pre-LO-01) — used for rollback.
_OLD_FUNCTION = """
CREATE OR REPLACE FUNCTION notify_event() RETURNS TRIGGER AS $$
  DECLARE
    record RECORD;
    payload JSON;
  BEGIN
    IF (TG_OP = 'DELETE') THEN
      record = OLD;
    ELSE
      record = NEW;
    END IF;

    payload = json_build_object('table', TG_TABLE_NAME,
                                'action', TG_OP,
                                'old', COALESCE(row_to_json(OLD), '{}'::json),
                                'new', COALESCE(row_to_json(NEW), '{}'::json));

    PERFORM pg_notify('events', payload::text);

    RETURN NULL;
  END;
  $$ LANGUAGE plpgsql;
"""


def upgrade():
    op.execute(_FUNCTION)


def downgrade():
    op.execute(_OLD_FUNCTION)
