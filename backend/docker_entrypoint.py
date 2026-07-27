"""Entrypoint for standalone QuantumPACS backend container.

Runs alembic migrations then starts Gunicorn.
Replaces the shell-based backend/docker-entrypoint.sh for distroless images.
"""
import os
import signal
import subprocess
import sys
import time


def main():
    skip_migrations = os.environ.get("SKIP_MIGRATIONS") == "1"

    if not skip_migrations:
        try:
            subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                timeout=60,
            )
        except Exception:
            pass

    gunicorn = subprocess.Popen(
        [
            "gunicorn", "app:app",
            "-k", "uvicorn.workers.UvicornWorker",
            "-c", "api_conf.py",
        ],
    )

    def _forward_signal(sig, frame):
        gunicorn.send_signal(sig)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _forward_signal)
    signal.signal(signal.SIGINT, _forward_signal)

    while True:
        time.sleep(1)
        if gunicorn.poll() is not None:
            sys.exit(gunicorn.returncode)


if __name__ == "__main__":
    main()