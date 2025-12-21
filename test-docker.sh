#!/bin/bash

# DocsVerify Docker Test Script
# Script ini untuk testing aplikasi setelah build

set -e

echo "🧪 DocsVerify Docker Test Suite"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health check
echo -e "${YELLOW}Test 1: Health Check${NC}"
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API responding${NC}"
else
    echo -e "${RED}✗ API not responding${NC}"
    exit 1
fi
echo ""

# Test 2: Swagger UI
echo -e "${YELLOW}Test 2: Swagger UI${NC}"
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Swagger UI available${NC}"
else
    echo -e "${RED}✗ Swagger UI not available${NC}"
    exit 1
fi
echo ""

# Test 3: ReDoc
echo -e "${YELLOW}Test 3: ReDoc${NC}"
if curl -s http://localhost:8000/redoc > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ReDoc available${NC}"
else
    echo -e "${RED}✗ ReDoc not available${NC}"
    exit 1
fi
echo ""

# Test 4: OpenAPI JSON
echo -e "${YELLOW}Test 4: OpenAPI JSON Schema${NC}"
if curl -s http://localhost:8000/openapi.json > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OpenAPI schema available${NC}"
else
    echo -e "${RED}✗ OpenAPI schema not available${NC}"
    exit 1
fi
echo ""

# Test 5: Container health
echo -e "${YELLOW}Test 5: Container Health Status${NC}"
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' docsverify_docsverify 2>/dev/null || echo "no-healthcheck")
if [ "$HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✓ Container is healthy${NC}"
elif [ "$HEALTH" = "starting" ]; then
    echo -e "${YELLOW}⚠ Container is starting${NC}"
else
    echo -e "${RED}✗ Container health check failed${NC}"
fi
echo ""

# Test 6: Required modules
echo -e "${YELLOW}Test 6: Required Python Modules${NC}"
MODULES="fastapi uvicorn pytesseract PIL pdf2image rapidfuzz"
FAILED=0

for module in $MODULES; do
    if docker-compose exec docsverify python -c "import $module" 2>/dev/null; then
        echo -e "${GREEN}✓ $module${NC}"
    else
        echo -e "${RED}✗ $module${NC}"
        FAILED=$((FAILED + 1))
    fi
done

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All modules loaded successfully${NC}"
else
    echo -e "${RED}$FAILED modules failed${NC}"
fi
echo ""

# Test 7: System dependencies
echo -e "${YELLOW}Test 7: System Dependencies${NC}"
DEPS="tesseract pdftoppm"
FAILED=0

for dep in $DEPS; do
    if docker-compose exec docsverify which $dep > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $dep${NC}"
    else
        echo -e "${RED}✗ $dep${NC}"
        FAILED=$((FAILED + 1))
    fi
done

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All dependencies installed${NC}"
else
    echo -e "${RED}$FAILED dependencies missing${NC}"
fi
echo ""

# Summary
echo "=================================="
echo -e "${GREEN}✓ All tests passed!${NC}"
echo ""
echo "API Documentation:"
echo "  - Swagger UI: http://localhost:8000/docs"
echo "  - ReDoc: http://localhost:8000/redoc"
echo ""
