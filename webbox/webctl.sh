#!/bin/bash

# YT Lite v3 Control Script
# Usage: ./webctl.sh [command]

COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="ytlite"

function show_help {
    echo "Usage: ./webctl.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up           Start services in background (docker-compose up -d)"
    echo "  down         Stop and remove containers (docker-compose down)"
    echo "  start        Start existing containers"
    echo "  stop         Stop running containers"
    echo "  restart      Restart all services"
    echo "  logs         Follow logs (Ctrl+C to exit)"
    echo "  status       Show container status (ps)"
    echo ""
    echo "Options:"
    echo "  --rebuild    Force rebuild of images (use with 'up' or standalone)"
    echo ""
}

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed."
    exit 1
fi

COMMAND=$1
shift # Shift to check for flags

case "$COMMAND" in
    up)
        if [[ "$1" == "--rebuild" ]]; then
            echo "Building and starting services..."
            docker-compose -f $COMPOSE_FILE up -d --build
        else
            echo "Starting services..."
            docker-compose -f $COMPOSE_FILE up -d
        fi
        ;;
    down)
        echo "Stopping and removing containers..."
        docker-compose -f $COMPOSE_FILE down
        ;;
    start)
        echo "Starting containers..."
        docker-compose -f $COMPOSE_FILE start
        ;;
    stop)
        echo "Stopping containers..."
        docker-compose -f $COMPOSE_FILE stop
        ;;
    restart)
        echo "Restarting services..."
        docker-compose -f $COMPOSE_FILE restart
        ;;
    logs)
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    status|ps)
        docker-compose -f $COMPOSE_FILE ps
        ;;
    --rebuild)
        # Standalone rebuild command
        echo "Rebuilding images..."
        docker-compose -f $COMPOSE_FILE build --no-cache
        ;;
    *)
        show_help
        exit 1
        ;;
esac
