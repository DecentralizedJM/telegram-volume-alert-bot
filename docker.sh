#!/bin/bash

# Volume Alert Bot Control Script

ACTION=${1:-"help"}

case $ACTION in
    start)
        echo "🚀 Starting Volume Alert Bot..."
        docker-compose up -d
        sleep 2
        docker-compose logs -f
        ;;
    stop)
        echo "⛔ Stopping Volume Alert Bot..."
        docker-compose down
        ;;
    logs)
        echo "📋 Volume Alert Bot Logs"
        docker-compose logs -f
        ;;
    restart)
        echo "🔄 Restarting Volume Alert Bot..."
        docker-compose restart
        sleep 2
        docker-compose logs -f
        ;;
    build)
        echo "🔨 Building Volume Alert Bot..."
        docker-compose build
        ;;
    status)
        echo "📊 Volume Alert Bot Status"
        docker-compose ps
        ;;
    *)
        echo "Usage: $0 {start|stop|logs|restart|build|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the bot"
        echo "  stop    - Stop the bot"
        echo "  logs    - View live logs"
        echo "  restart - Restart the bot"
        echo "  build   - Build the Docker image"
        echo "  status  - Show status"
        ;;
esac
