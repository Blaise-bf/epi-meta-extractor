#!/bin/bash
# =================================================================
# Production Deployment Script for Digital Ocean
# =================================================================
# This script automates the deployment of Epi Meta Extractor to a
# Digital Ocean droplet (or any Docker-enabled VPS).
#
# Usage:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
# =================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"

echo -e "${GREEN}Epi Meta Extractor — Production Deployment${NC}"
echo "=========================================="

# -----------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: $ENV_FILE not found!${NC}"
    echo "Please copy .env.example to .env and configure it first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    exit 1
fi

# -----------------------------------------------------------------
# Pull latest images and build
# -----------------------------------------------------------------
echo -e "${YELLOW}Building production images...${NC}"
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" build --no-cache

# -----------------------------------------------------------------
# Start services
# -----------------------------------------------------------------
echo -e "${YELLOW}Starting services...${NC}"
docker compose -f "$COMPOSE_FILE" up -d

# -----------------------------------------------------------------
# Wait for health checks
# -----------------------------------------------------------------
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check MongoDB
if docker compose -f "$COMPOSE_FILE" ps | grep -q "mongodb.*healthy"; then
    echo -e "${GREEN}  MongoDB is healthy${NC}"
else
    echo -e "${RED}  MongoDB health check pending...${NC}"
fi

# Check Backend
if docker compose -f "$COMPOSE_FILE" ps | grep -q "backend.*healthy"; then
    echo -e "${GREEN}  Backend is healthy${NC}"
else
    echo -e "${RED}  Backend health check pending...${NC}"
fi

# -----------------------------------------------------------------
# Display status
# -----------------------------------------------------------------
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
docker compose -f "$COMPOSE_FILE" ps
echo ""
echo "Logs:"
echo "  docker compose -f $COMPOSE_FILE logs -f backend"
echo "  docker compose -f $COMPOSE_FILE logs -f frontend"
echo "  docker compose -f $COMPOSE_FILE logs -f nginx"
echo ""
echo "To stop:"
echo "  docker compose -f $COMPOSE_FILE down"
echo ""
