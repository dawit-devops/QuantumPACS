"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-22

"""

from alembic import op


revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS intarray")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username CITEXT NOT NULL,
        password TEXT NOT NULL,
        admin BOOLEAN NOT NULL DEFAULT FALSE,
        status TEXT NOT NULL DEFAULT 'active',
        created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc')
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id SERIAL PRIMARY KEY,
        patient_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        birth_date TEXT,
        sex TEXT,
        meta JSONB
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS studies (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER NOT NULL REFERENCES patients(id),
        study_id TEXT NOT NULL,
        description TEXT,
        UNIQUE(patient_id, study_id)
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS series (
        id SERIAL PRIMARY KEY,
        study_id INTEGER NOT NULL REFERENCES studies(id),
        number TEXT NOT NULL,
        modality TEXT NOT NULL,
        description TEXT,
        UNIQUE(study_id, number)
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id SERIAL PRIMARY KEY,
        patient_id INTEGER NOT NULL REFERENCES patients(id),
        study_id INTEGER NOT NULL REFERENCES studies(id),
        series_id INTEGER NOT NULL REFERENCES series(id),
        name TEXT NOT NULL,
        indexed BOOLEAN NOT NULL DEFAULT FALSE,
        hash TEXT NOT NULL,
        created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        deleted BOOLEAN NOT NULL DEFAULT FALSE,
        meta JSONB,
        tools_state JSONB
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS file_changes (
        id SERIAL PRIMARY KEY,
        file_id INTEGER NOT NULL REFERENCES files(id),
        created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        by_user_id INTEGER NOT NULL REFERENCES users(id),
        type TEXT NOT NULL,
        old TEXT,
        new TEXT
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS replicas (
        id SERIAL PRIMARY KEY,
        type TEXT NOT NULL,
        location TEXT NOT NULL UNIQUE,
        master BOOLEAN NOT NULL DEFAULT FALSE,
        delay INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        total INTEGER NOT NULL DEFAULT 0,
        meta JSONB
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS replica_files (
        id SERIAL,
        replica_id INTEGER NOT NULL REFERENCES replicas(id),
        file_id INTEGER NOT NULL REFERENCES files(id),
        location TEXT NOT NULL,
        status INTEGER NOT NULL,
        created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        updated TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        meta JSONB,
        UNIQUE (replica_id, file_id)
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        log TEXT NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS shared_files (
        id SERIAL PRIMARY KEY,
        created TIMESTAMP NOT NULL DEFAULT (now() at time zone 'utc'),
        expires TIMESTAMP NOT NULL,
        file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
        hash TEXT NOT NULL
    );
    """)

    op.execute("CREATE INDEX IF NOT EXISTS users_username ON users(username)")
    op.execute("CREATE INDEX IF NOT EXISTS patients_patient_id ON patients(patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS studies_study_id ON studies(study_id)")
    op.execute("CREATE INDEX IF NOT EXISTS series_number ON series(number)")
    op.execute("CREATE INDEX IF NOT EXISTS files_name ON files(name)")
    op.execute("CREATE INDEX IF NOT EXISTS files_hash ON files(hash)")
    op.execute("CREATE INDEX IF NOT EXISTS file_changes_file_id ON file_changes(file_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS replicas_master_unique ON replicas(master) WHERE master = TRUE")
    op.execute("CREATE INDEX IF NOT EXISTS replica_files_replica_id ON replica_files(replica_id)")
    op.execute("CREATE INDEX IF NOT EXISTS shared_files_hash ON shared_files(hash)")

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
    op.execute("DROP TRIGGER IF EXISTS notify_replica_event ON replicas")
    op.execute("""
    CREATE TRIGGER notify_replica_event
    AFTER INSERT OR UPDATE OR DELETE ON replicas
      FOR EACH ROW EXECUTE PROCEDURE notify_event();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS notify_replica_event ON replicas")
    op.execute("DROP FUNCTION IF EXISTS notify_event()")
    op.execute("DROP TABLE IF EXISTS shared_files CASCADE")
    op.execute("DROP TABLE IF EXISTS replica_files CASCADE")
    op.execute("DROP TABLE IF EXISTS file_changes CASCADE")
    op.execute("DROP TABLE IF EXISTS logs CASCADE")
    op.execute("DROP TABLE IF EXISTS replicas CASCADE")
    op.execute("DROP TABLE IF EXISTS files CASCADE")
    op.execute("DROP TABLE IF EXISTS series CASCADE")
    op.execute("DROP TABLE IF EXISTS studies CASCADE")
    op.execute("DROP TABLE IF EXISTS patients CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
