#!/bin/bash
# Quick Start Script for RAG Pipeline Deployment
# Requires: sudo access to start PostgreSQL

set -e  # Exit on error

echo "=========================================="
echo "RAG Pipeline Deployment - Quick Start"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL not found. Please install:${NC}"
    echo "   sudo apt install postgresql postgresql-contrib"
    exit 1
fi

echo -e "${GREEN}✓${NC} PostgreSQL is installed"

# Step 1: Start PostgreSQL
echo ""
echo "Step 1: Starting PostgreSQL service..."
sudo service postgresql start

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} PostgreSQL started successfully"
else
    echo -e "${RED}❌ Failed to start PostgreSQL${NC}"
    exit 1
fi

# Step 2: Check connection
echo ""
echo "Step 2: Checking PostgreSQL connection..."
pg_isready -h localhost -p 5432

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} PostgreSQL is accepting connections"
else
    echo -e "${RED}❌ PostgreSQL is not accepting connections${NC}"
    exit 1
fi

# Step 3: Create database
echo ""
echo "Step 3: Creating dataforge database..."

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'dataforge'" | grep -q 1 || \
sudo -u postgres psql <<EOF
CREATE DATABASE dataforge;
CREATE USER dataforge_user WITH PASSWORD 'dataforge_dev_password';
GRANT ALL PRIVILEGES ON DATABASE dataforge TO dataforge_user;
EOF

echo -e "${GREEN}✓${NC} Database 'dataforge' ready"

# Step 4: Install pgvector extension
echo ""
echo "Step 4: Installing pgvector extension..."
sudo -u postgres psql -d dataforge -c "CREATE EXTENSION IF NOT EXISTS vector;"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} pgvector extension installed"
else
    echo -e "${YELLOW}⚠${NC} pgvector may not be installed (not critical for keyword search)"
fi

# Step 5: Update .env file
echo ""
echo "Step 5: Updating DataForge .env configuration..."

ENV_FILE="/home/charles/projects/Coding2025/Forge/DataForge/.env"

if [ -f "$ENV_FILE" ]; then
    # Backup original
    cp "$ENV_FILE" "$ENV_FILE.backup"

    # Replace SQLite with PostgreSQL URL
    sed -i 's|^DATABASE_URL=sqlite:///./dataforge.db|DATABASE_URL=postgresql://dataforge_user:dataforge_dev_password@localhost:5432/dataforge|' "$ENV_FILE"

    echo -e "${GREEN}✓${NC} .env updated (backup saved as .env.backup)"
else
    echo -e "${RED}❌ .env file not found at $ENV_FILE${NC}"
    exit 1
fi

# Step 6: Run migration
echo ""
echo "Step 6: Running database migration..."
cd /home/charles/projects/Coding2025/Forge/DataForge

python3 -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Migration completed successfully"
else
    echo -e "${RED}❌ Migration failed${NC}"
    exit 1
fi

# Step 7: Verify migration
echo ""
echo "Step 7: Verifying migration..."
CURRENT_REVISION=$(python3 -m alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' | head -1)

if [ "$CURRENT_REVISION" == "7f3a8b9c2d4e" ]; then
    echo -e "${GREEN}✓${NC} Migration at correct revision: $CURRENT_REVISION"
else
    echo -e "${YELLOW}⚠${NC} Unexpected revision: $CURRENT_REVISION (expected: 7f3a8b9c2d4e)"
fi

# Step 8: Verify search_vector column
echo ""
echo "Step 8: Verifying search_vector column..."
COLUMN_EXISTS=$(psql -d dataforge -U dataforge_user -h localhost -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='chunks' AND column_name='search_vector';" 2>/dev/null | tr -d ' ')

if [ "$COLUMN_EXISTS" == "search_vector" ]; then
    echo -e "${GREEN}✓${NC} search_vector column exists"
else
    echo -e "${RED}❌ search_vector column not found${NC}"
fi

# Success
echo ""
echo "=========================================="
echo -e "${GREEN}✅ RAG Pipeline Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start DataForge service:"
echo "   cd /home/charles/projects/Coding2025/Forge/DataForge"
echo "   uvicorn app.main:app --reload --port 8001"
echo ""
echo "2. Test endpoints:"
echo "   curl -X POST http://localhost:8001/api/search/hybrid \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"test\", \"limit\": 5}'"
echo ""
echo "3. Run validation tests:"
echo "   cd /home/charles/projects/Coding2025/Forge"
echo "   python3 test_rag_refactoring.py"
echo ""
echo "Documentation: DEPLOYMENT_GUIDE_RAG.md"
