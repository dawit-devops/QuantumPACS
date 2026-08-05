"""Fix notify_event trigger function to handle NULL OLD/NEW

Revision ID: 025
Revises: 024
Create Date: 2026-07-28

Why
---
Fixes the notify_event() trigger function to use COALESCE on row_to_json(OLD)
and row_to_json(NEW), preventing NULL values in the payload JSON for INSERT
and DELETE operations respectively — which caused downstream parsing failures.

Data Migration
--------------
None — function-only change. Replaces the existing function in-place.

Rollback
--------
Restores the original notify_event() function without COALESCE.

References
----------
- GitHub issue: notify_event payload NULL for INSERT/DELETE
"""

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
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
    """)


def downgrade():
    op.execute("""
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
                                    'old', row_to_json(OLD),
                                    'new', row_to_json(NEW));
        PERFORM pg_notify('events', payload::text);
        RETURN NULL;
      END;
      $$ LANGUAGE plpgsql;
    """)
