#!/bin/bash
set -e

CMD=${1:-status}

case "$CMD" in
  start)
    echo "Starting QuantumPACS dev services..."
    docker compose up -d 2>&1 || true
    systemctl --user start quantumpacs-backend.service
    systemctl --user start quantumpacs-frontend.service
    echo "Done."
    ;;
  stop)
    echo "Stopping QuantumPACS dev services..."
    systemctl --user stop quantumpacs-backend.service
    systemctl --user stop quantumpacs-frontend.service
    echo "Done."
    ;;
  restart)
    echo "Restarting QuantumPACS dev services..."
    systemctl --user restart quantumpacs-backend.service
    systemctl --user restart quantumpacs-frontend.service
    echo "Done."
    ;;
  status)
    echo "=== QuantumPACS Backend ==="
    systemctl --user status quantumpacs-backend.service --no-pager 2>&1 | head -10
    echo ""
    echo "=== QuantumPACS Frontend ==="
    systemctl --user status quantumpacs-frontend.service --no-pager 2>&1 | head -10
    echo ""
    echo "=== Health Check ==="
    echo -n "Backend (8080): "; curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/health 2>&1 || echo "down"
    echo ""
    echo -n "Frontend (5173): "; curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>&1 || echo "down"
    echo ""
    ;;
  logs)
    journalctl --user -u quantumpacs-backend.service -f --no-pager 2>&1
    ;;
  logs-fe)
    journalctl --user -u quantumpacs-frontend.service -f --no-pager 2>&1
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs|logs-fe}"
    exit 1
    ;;
esac
