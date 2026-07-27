.PHONY: build up down restart logs status clean scan

# Docker image tags
BACKEND_IMAGE  ?= quantumpacs-backend
FRONTEND_IMAGE ?= quantumpacs-frontend
POSTGRES_IMAGE ?= quantumpacs-postgres
TAG            ?= latest

# Build all images
build: build-backend build-frontend build-postgres

build-backend:
	docker build -t $(BACKEND_IMAGE):$(TAG) -f backend/Dockerfile backend/

build-frontend:
	docker build -t $(FRONTEND_IMAGE):$(TAG) -f frontend/Dockerfile frontend/

build-postgres:
	docker build -t $(POSTGRES_IMAGE):16 -f docker/postgres/Dockerfile docker/postgres

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Restart all services
restart: down up

# Tail logs
logs:
	docker compose logs -f

# Service status
status:
	docker compose ps

# Clean volumes and images
clean:
	docker compose down -v
	docker rmi $(BACKEND_IMAGE):$(TAG) $(FRONTEND_IMAGE):$(TAG) 2>/dev/null; true

# Vulnerability scan (requires Docker Scout)
scan:
ifeq ($(shell docker scout --version 2>/dev/null),)
	@echo "Docker Scout not installed. Install it via:"
	@echo "  brew install docker-scout"
	@echo "Or use Trivy:"
	@echo "  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image $(BACKEND_IMAGE):$(TAG)"
else
	docker scout quickview $(BACKEND_IMAGE):$(TAG)
	docker scout quickview $(FRONTEND_IMAGE):$(TAG)
endif

# Build and start everything
all: build up
	@echo "All services built and started. Use 'make logs' to follow output."