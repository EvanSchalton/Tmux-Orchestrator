#!/bin/bash
# Container deployment script for tmux-orchestrator
set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse command line arguments
COMMAND="${1:-help}"
PROFILE="${2:-default}"

show_help() {
    echo -e "${BLUE}Tmux Orchestrator Container Deployment${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo ""
    echo "Usage: $0 <command> [profile]"
    echo ""
    echo "Commands:"
    echo "  build      - Build container images"
    echo "  start      - Start services"
    echo "  stop       - Stop services"
    echo "  restart    - Restart services"
    echo "  logs       - Show service logs"
    echo "  status     - Show service status"
    echo "  test       - Run tests in containers"
    echo "  shell      - Open shell in CLI tools container"
    echo "  clean      - Clean up containers and volumes"
    echo "  help       - Show this help"
    echo ""
    echo "Profiles:"
    echo "  default    - MCP server + CLI tools"
    echo "  legacy     - Include legacy MCP server"
    echo "  testing    - Include test runner"
    echo "  full       - All services"
    echo ""
    echo "Examples:"
    echo "  $0 start            # Start default services"
    echo "  $0 start legacy     # Start with legacy MCP"
    echo "  $0 test             # Run tests"
    echo "  $0 shell            # Open CLI tools shell"
}

build_images() {
    echo -e "${GREEN}Building container images...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" build --parallel
    echo -e "${GREEN}✅ Build complete${NC}"
}

start_services() {
    echo -e "${GREEN}Starting services (profile: $PROFILE)...${NC}"
    cd "$PROJECT_ROOT"

    case "$PROFILE" in
        "legacy")
            docker-compose -f "$COMPOSE_FILE" --profile legacy up -d
            ;;
        "testing")
            docker-compose -f "$COMPOSE_FILE" --profile testing up -d
            ;;
        "full")
            docker-compose -f "$COMPOSE_FILE" --profile legacy --profile testing up -d
            ;;
        *)
            docker-compose -f "$COMPOSE_FILE" up -d mcp-server cli-tools
            ;;
    esac

    echo ""
    echo -e "${GREEN}✅ Services started${NC}"
    echo ""
    echo "Service URLs:"
    echo "  FastMCP Server: http://localhost:8000"
    if [[ "$PROFILE" == "legacy" || "$PROFILE" == "full" ]]; then
        echo "  Legacy MCP:     http://localhost:8001"
    fi
    echo ""
    echo "Next steps:"
    echo "  Check status: $0 status"
    echo "  View logs:    $0 logs"
    echo "  CLI shell:    $0 shell"
}

stop_services() {
    echo -e "${YELLOW}Stopping services...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✅ Services stopped${NC}"
}

restart_services() {
    echo -e "${YELLOW}Restarting services...${NC}"
    stop_services
    sleep 2
    start_services
}

show_logs() {
    echo -e "${BLUE}Service logs (follow mode - Ctrl+C to exit):${NC}"
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" logs -f
}

show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""

    # Test CLI availability
    echo -e "${BLUE}CLI Test:${NC}"
    if docker-compose -f "$COMPOSE_FILE" exec -T cli-tools tmux-orc --version 2>/dev/null; then
        echo -e "${GREEN}✅ CLI tools available${NC}"
    else
        echo -e "${RED}❌ CLI tools not available${NC}"
    fi

    # Test MCP server
    echo -e "${BLUE}MCP Server Test:${NC}"
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ FastMCP server responsive${NC}"
    else
        echo -e "${RED}❌ FastMCP server not responsive${NC}"
    fi
}

run_tests() {
    echo -e "${GREEN}Running tests in container...${NC}"
    cd "$PROJECT_ROOT"

    # Start test runner if not running
    docker-compose -f "$COMPOSE_FILE" --profile testing up -d test-runner

    # Execute tests
    docker-compose -f "$COMPOSE_FILE" exec test-runner python -m pytest --tb=short -v

    echo -e "${GREEN}✅ Tests complete${NC}"
}

open_shell() {
    echo -e "${GREEN}Opening CLI tools shell...${NC}"
    cd "$PROJECT_ROOT"

    # Ensure CLI tools container is running
    docker-compose -f "$COMPOSE_FILE" up -d cli-tools

    # Open interactive shell
    docker-compose -f "$COMPOSE_FILE" exec cli-tools bash
}

clean_up() {
    echo -e "${YELLOW}Cleaning up containers and volumes...${NC}"
    cd "$PROJECT_ROOT"

    # Stop and remove containers
    docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans

    # Remove images (optional)
    read -p "Remove built images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" down --rmi all
        echo -e "${GREEN}✅ Images removed${NC}"
    fi

    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Change to project root
cd "$PROJECT_ROOT"

# Execute command
case "$COMMAND" in
    "build")
        build_images
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "test")
        run_tests
        ;;
    "shell")
        open_shell
        ;;
    "clean")
        clean_up
        ;;
    "help"|*)
        show_help
        ;;
esac
