.PHONY: help build up down logs restart test clean

help:
	@echo "DocsVerify Docker Commands:"
	@echo "============================="
	@echo "make build       - Build Docker image"
	@echo "make up          - Start container"
	@echo "make down        - Stop and remove container"
	@echo "make logs        - View container logs"
	@echo "make logs-f      - Follow container logs"
	@echo "make restart     - Restart container"
	@echo "make test        - Test API health"
	@echo "make shell       - Access container shell"
	@echo "make clean       - Remove all Docker resources"
	@echo "make rebuild     - Rebuild image from scratch"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "✓ Container started on http://localhost:8000"

down:
	docker-compose down

logs:
	docker-compose logs docsverify

logs-f:
	docker-compose logs -f docsverify

restart:
	docker-compose restart

test:
	@curl -s http://localhost:8000/ | python -m json.tool || echo "API not responding"

shell:
	docker-compose exec docsverify /bin/bash

clean:
	docker-compose down -v
	docker image rm docsverify_docsverify || true
	@echo "✓ Docker resources cleaned up"

rebuild:
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✓ Image rebuilt and container restarted"

validate-requirements:
	@echo "Validating requirements.txt..."
	@docker-compose exec docsverify pip check || true

status:
	@echo "Container Status:"
	@docker-compose ps
	@echo ""
	@echo "Health Check:"
	@docker-compose ps --format table

docs:
	@echo "API Documentation available at:"
	@echo "- Swagger UI: http://localhost:8000/docs"
	@echo "- ReDoc: http://localhost:8000/redoc"
