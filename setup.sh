#!/bin/bash
set -e

echo "🎬 Vision AI Casting - Setup Script"
echo "===================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $1 is installed${NC}"
        return 0
    fi
}

echo ""
echo "Checking prerequisites..."
check_command docker || exit 1
check_command docker-compose || exit 1
check_command git || exit 1

# Check optional commands
echo ""
echo "Optional tools:"
check_command python3
check_command node

# Setup environment
echo ""
echo "Setting up environment..."

if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo -e "${YELLOW}⚠️  Created backend/.env from example. Please edit it with your credentials.${NC}"
fi

if [ ! -f frontend/.env.local ]; then
    cp frontend/.env.example frontend/.env.local
    echo -e "${YELLOW}⚠️  Created frontend/.env.local from example. Please edit it with your credentials.${NC}"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p backend/logs
mkdir -p frontend/.next
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/datasources
mkdir -p nginx/ssl

# Generate self-signed SSL cert for local development
if [ ! -f nginx/ssl/cert.pem ]; then
    echo ""
    echo "Generating self-signed SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=BR/ST=SP/L=Sao Paulo/O=Vision AI/CN=localhost" \
        2>/dev/null || echo -e "${YELLOW}⚠️  Could not generate SSL certificate. Install openssl.${NC}"
fi

# Start services
echo ""
echo "Starting services with Docker Compose..."
docker-compose up -d

# Wait for database
echo ""
echo "Waiting for database to be ready..."
until docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 1
done
echo -e "${GREEN} ✅ Database is ready${NC}"

# Run migrations
echo ""
echo "Running database migrations..."
cd backend
if [ -d "venv" ]; then
    source venv/bin/activate
fi
pip install -q alembic asyncpg
alembic upgrade head
cd ..

echo ""
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}🚀 Setup complete!${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo "Services:"
echo "  Frontend:    http://localhost:3000"
echo "  Backend API: http://localhost:8000/docs"
echo "  Database:    localhost:5432"
echo "  Redis:       localhost:6379"
echo "  Prometheus:  http://localhost:9090"
echo "  Grafana:     http://localhost:3001"
echo ""
echo "Useful commands:"
echo "  make dev          - Start development environment"
echo "  make test         - Run all tests"
echo "  make logs         - View logs"
echo "  make db-reset     - Reset database"
echo ""
echo -e "${YELLOW}⚠️  Don't forget to:${NC}"
echo "  1. Edit backend/.env with your API keys"
echo "  2. Edit frontend/.env.local with your settings"
echo "  3. Run 'make migrate' after model changes"
echo ""
