#!/bin/bash

# Local development helper script for JAO project

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if docker and docker-compose are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Dependencies check passed!"
}

# Setup environment file
setup_env() {
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        print_success ".env file created! Please review and update the values if needed."
    else
        print_status ".env file already exists."
    fi
}

# Build and start services
start() {
    print_status "Starting development environment..."
    check_dependencies
    setup_env
    
    docker-compose build
    docker-compose up -d
    
    print_success "Development environment started!"
    print_status "Services running at:"
    print_status "  - JAO Backend: http://localhost:8000"
    print_status "  - JAO Web: http://localhost:8001"
    print_status "  - PostgreSQL: localhost:5432"
    print_status "  - Redis: localhost:6379"
}

# Stop services
stop() {
    print_status "Stopping development environment..."
    docker-compose down
    print_success "Development environment stopped!"
}

# Restart services
restart() {
    print_status "Restarting development environment..."
    docker-compose restart
    print_success "Development environment restarted!"
}

# View logs
logs() {
    if [ -z "$1" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$1"
    fi
}

# Clean up everything
clean() {
    print_warning "This will remove all containers, volumes, and images related to this project."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up..."
        docker-compose down -v --remove-orphans
        docker-compose build --no-cache
        print_success "Cleanup completed!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Execute commands in containers
exec_backend() {
    docker-compose exec jao-backend "${@}"
}

exec_web() {
    docker-compose exec jao-web "${@}"
}

# Database operations
db_migrate() {
    print_status "Running database migrations..."
    docker-compose exec jao-backend poetry run python src/manage.py migrate
    print_success "Database migrations completed!"
}

db_shell() {
    print_status "Opening database shell..."
    docker-compose exec db psql -U jao_user -d jao_dev
}

# Show help
show_help() {
    echo "JAO Local Development Helper"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start         Start the development environment"
    echo "  stop          Stop the development environment"
    echo "  restart       Restart the development environment"
    echo "  logs [service] Show logs for all services or specific service"
    echo "  clean         Clean up all containers and volumes"
    echo "  db:migrate    Run database migrations"
    echo "  db:shell      Open database shell"
    echo "  backend [cmd] Execute command in backend container"
    echo "  web [cmd]     Execute command in web container"
    echo "  help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                                    # Start all services"
    echo "  $0 logs jao-backend                        # Show backend logs"
    echo "  $0 backend poetry run python src/manage.py shell  # Django shell"
    echo "  $0 web npm run watch                       # Watch frontend changes"
}

# Main script logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$2"
        ;;
    clean)
        clean
        ;;
    db:migrate)
        db_migrate
        ;;
    db:shell)
        db_shell
        ;;
    backend)
        shift
        exec_backend "$@"
        ;;
    web)
        shift
        exec_web "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        if [ -z "$1" ]; then
            show_help
        else
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
        fi
        ;;
esac
