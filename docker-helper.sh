#!/bin/bash

# Docker Compose Helper Script
# This script helps with Docker operations when docker-compose has compatibility issues
# Usage: ./docker-helper.sh build|up|down|logs|test

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SERVICE_NAME="docsverify"
CONTAINER_NAME="docsverify-app"
IMAGE_NAME="docsverify:latest"

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ DocsVerify Docker Helper Script        ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
}

print_error() {
    echo -e "${RED}✗ Error: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

show_help() {
    print_header
    echo "Available commands:"
    echo ""
    echo "  ./docker-helper.sh build        - Build Docker image"
    echo "  ./docker-helper.sh up           - Start container"
    echo "  ./docker-helper.sh down         - Stop container"
    echo "  ./docker-helper.sh logs         - View logs"
    echo "  ./docker-helper.sh logs-f       - Follow logs (realtime)"
    echo "  ./docker-helper.sh test         - Test API health"
    echo "  ./docker-helper.sh status       - Show container status"
    echo "  ./docker-helper.sh shell        - Access container shell"
    echo "  ./docker-helper.sh restart      - Restart container"
    echo "  ./docker-helper.sh clean        - Remove container and image"
    echo ""
}

build_image() {
    print_header
    echo "Building Docker image: $IMAGE_NAME"
    echo ""
    docker build --no-cache -t $IMAGE_NAME .
    print_success "Image built successfully: $IMAGE_NAME"
}

start_container() {
    print_header
    echo "Starting container: $CONTAINER_NAME"
    echo ""
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Container already exists, starting it..."
        docker start $CONTAINER_NAME
    else
        print_info "Creating new container..."
        docker run -d \
            --name $CONTAINER_NAME \
            -p 8000:8000 \
            --restart unless-stopped \
            -v $(pwd)/uploads:/app/uploads \
            -v $(pwd)/logs:/app/logs \
            -e PYTHONUNBUFFERED=1 \
            --healthcheck=cmd:'python -c "import requests; requests.get(\"http://localhost:8000/\", timeout=5)"' \
            --healthcheck-interval=30s \
            --healthcheck-timeout=10s \
            --healthcheck-retries=3 \
            --healthcheck-start-period=5s \
            $IMAGE_NAME
    fi
    
    print_success "Container started: $CONTAINER_NAME"
    echo ""
    echo "Access application at: http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
}

stop_container() {
    print_header
    echo "Stopping container: $CONTAINER_NAME"
    
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker stop $CONTAINER_NAME
        print_success "Container stopped"
    else
        print_info "Container is not running"
    fi
}

view_logs() {
    print_header
    echo "Container logs (last 100 lines):"
    echo ""
    docker logs --tail=100 $CONTAINER_NAME || print_error "Container not found"
}

follow_logs() {
    print_header
    echo "Following container logs (Ctrl+C to exit)..."
    echo ""
    docker logs -f $CONTAINER_NAME || print_error "Container not found"
}

test_api() {
    print_header
    echo "Testing API health..."
    echo ""
    
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_success "API is responding"
        echo ""
        echo "Response:"
        curl -s http://localhost:8000/ | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/
    else
        print_error "API is not responding on http://localhost:8000"
        echo ""
        echo "Check if container is running:"
        docker ps --filter "name=$CONTAINER_NAME"
    fi
}

show_status() {
    print_header
    echo "Container Status:"
    echo ""
    
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        echo ""
        echo "Health Check:"
        docker inspect $CONTAINER_NAME --format='{{json .State.Health}}' | python3 -m json.tool 2>/dev/null || echo "No health data"
    else
        print_error "Container not found"
    fi
}

access_shell() {
    print_header
    echo "Accessing container shell..."
    echo ""
    docker exec -it $CONTAINER_NAME /bin/bash || print_error "Container not found or not running"
}

restart_container() {
    print_header
    echo "Restarting container: $CONTAINER_NAME"
    
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker restart $CONTAINER_NAME
        print_success "Container restarted"
    else
        print_error "Container not found"
    fi
}

clean_all() {
    print_header
    echo "Cleaning up Docker resources..."
    echo ""
    
    # Stop container
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Stopping container..."
        docker stop $CONTAINER_NAME
    fi
    
    # Remove container
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_info "Removing container..."
        docker rm $CONTAINER_NAME
    fi
    
    # Remove image
    if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
        print_info "Removing image..."
        docker rmi $IMAGE_NAME
    fi
    
    print_success "Cleanup complete"
}

# Main script
case "${1:-help}" in
    build)
        build_image
        ;;
    up)
        if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
            print_error "Image not found. Please run: ./docker-helper.sh build"
            exit 1
        fi
        start_container
        ;;
    down)
        stop_container
        ;;
    logs)
        view_logs
        ;;
    logs-f|logs-follow)
        follow_logs
        ;;
    test)
        test_api
        ;;
    status)
        show_status
        ;;
    shell)
        access_shell
        ;;
    restart)
        restart_container
        ;;
    clean)
        clean_all
        ;;
    help|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
