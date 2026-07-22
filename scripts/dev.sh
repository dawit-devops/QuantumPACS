#!/bin/bash
set -e

CMD=${1:-status}

case "$CMD" in
  start)
    echo "Starting OpenPACS dev services..."
    docker compose up -d 2>&1 || true
    systemctl --user start openpacs-backend.service
    systemctl --user start openpacs-frontend.service
    echo "Done."
    ;;
  stop)
    echo "Stopping OpenPACS dev services..."
    systemctl --user stop openpacs-backend.service
    systemctl --user stop openpacs-frontend.service
    echo "Done."
    ;;
  restart)
    echo "Restarting OpenPACS dev services..."
    systemctl --user restart openpacs-backend.service
    systemctl --user restart openpacs-frontend.service
    echo "Done."
    ;;
  status)
    echo "=== OpenPACS Backend ==="
    systemctl --user status openpacs-backend.service --no-pager 2>&1 | head -10
    echo ""
    echo "=== OpenPACS Frontend ==="
    systemctl --user status openpacs-frontend.service --no-pager 2>&1 | head -10
    echo ""
    echo "=== Health Check ==="
    echo -n "Backend (8080): "; curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/health 2>&1 || echo "down"
    echo ""
    echo -n "Frontend (5173): "; curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>&1 || echo "down"
    echo ""
    ;;
  logs)
    journalctl --user -u openpacs-backend.service -f --no-pager 2>&1
    ;;
  logs-fe)
    journalctl --user -u openpacs-frontend.service -f --no-pager 2>&1
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs|logs-fe}"
    exit 1
    ;;
esac
