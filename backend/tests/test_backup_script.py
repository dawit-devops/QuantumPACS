import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_SCRIPT = REPO_ROOT / 'scripts' / 'backup_db.sh'
BACKUP_ALL = REPO_ROOT / 'scripts' / 'backup_all.sh'
BASH = shutil.which('bash')


@pytest.fixture
def backup_env(tmp_path):
    env = dict(os.environ)
    env.update({
        'DATABASE_URL': 'postgresql://quantumpacs:mainpw@localhost:5432/quantumpacs',
        'BACKUP_DIR': str(tmp_path / 'backups'),
        'PATH': str(tmp_path / 'bin') + os.pathsep + env['PATH'],
    })
    return tmp_path, env


def _fake_psql(tmp_path, rows: str):
    """psql that prints tab-free registry rows; empties keep their separator.

    The registry is read with \x1f (unit separator) fields so bash `read` does
    not collapse consecutive empty fields (tabs are IFS whitespace and DO).
    """
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    psql = bin_dir / 'psql'
    psql.write_text(f'#!/bin/bash\nprintf \'{rows}\'\n')
    psql.chmod(psql.stat().st_mode | stat.S_IEXEC)


def _tool_bin_dir(tmp_path):
    """A PATH with the script's required tools but deliberately no psql."""
    bin_dir = tmp_path / 'emptybin'
    bin_dir.mkdir()
    for tool in ('date', 'mkdir', 'find', 'wc', 'grep', 'sed', 'tr', 'head'):
        src = shutil.which(tool)
        if src:
            (bin_dir / tool).symlink_to(src)
    return str(bin_dir)


class TestBackupScriptDryRun:
    def test_dry_run_prints_main_dump_without_creating_files(self, backup_env):
        tmp_path, env = backup_env
        result = subprocess.run(
            [BASH, str(BACKUP_SCRIPT), '--dry-run'],
            capture_output=True, text=True, env=env, timeout=60,
        )
        assert result.returncode == 0
        assert 'DRY-RUN: pg_dump postgresql://quantumpacs:mainpw@localhost:5432/quantumpacs' in result.stdout
        assert 'DRY-RUN: find' in result.stdout
        assert list((tmp_path / 'backups').iterdir()) == []

    def test_dry_run_prints_tenant_dumps_using_registry_values(self, backup_env):
        tmp_path, env = backup_env
        rows = '\n'.join([
            'acme_clinic\x1f127.0.0.1\x1f5432\x1fquantumpacs\x1facmepw',
            'beta_rad\x1f10.0.0.5\x1f5433\x1f\x1fbetaownerpw',
            'gamma\x1f\x1f\x1f\x1f',
        ])
        _fake_psql(tmp_path, rows)
        result = subprocess.run(
            [BASH, str(BACKUP_SCRIPT), '--dry-run'],
            capture_output=True, text=True, env=env, timeout=60,
        )
        assert result.returncode == 0
        assert 'DRY-RUN: pg_dump postgresql://quantumpacs:acmepw@127.0.0.1:5432/acme_clinic' in result.stdout
        # empty db_user falls back to the main-DB user
        assert 'DRY-RUN: pg_dump postgresql://quantumpacs:betaownerpw@10.0.0.5:5433/beta_rad' in result.stdout
        # all-empty row still dumps the DB with main-DB defaults
        assert 'DRY-RUN: pg_dump postgresql://quantumpacs:mainpw@localhost:5432/gamma' in result.stdout
        assert result.stdout.count('DRY-RUN: pg_dump') == 4
        assert list((tmp_path / 'backups').iterdir()) == []

    def test_dry_run_warns_when_psql_missing_but_main_dump_works(self, backup_env):
        tmp_path, env = backup_env
        env['PATH'] = _tool_bin_dir(tmp_path)
        result = subprocess.run(
            [BASH, str(BACKUP_SCRIPT), '--dry-run'],
            capture_output=True, text=True, env=env, timeout=60,
        )
        assert result.returncode == 0
        assert 'DRY-RUN: pg_dump postgresql://quantumpacs:mainpw@localhost:5432/quantumpacs' in result.stdout
        assert 'psql not found' in result.stderr

    def test_backup_all_wrapper_forwards_dry_run(self, backup_env):
        _, env = backup_env
        result = subprocess.run(
            [BASH, str(BACKUP_ALL), '--dry-run'],
            capture_output=True, text=True, env=env, timeout=60,
        )
        assert result.returncode == 0
        assert 'DRY-RUN: pg_dump' in result.stdout

    def test_unknown_argument_rejected(self, backup_env):
        _, env = backup_env
        result = subprocess.run(
            [BASH, str(BACKUP_SCRIPT), '--bogus'],
            capture_output=True, text=True, env=env, timeout=60,
        )
        assert result.returncode == 2
        assert 'unknown argument' in result.stderr
