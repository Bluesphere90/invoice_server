#!/bin/bash
# ===========================================
# Invoice Server - Deployment Setup Script
# ===========================================
# Run this script to setup the project on Ubuntu

set -e

echo "========================================"
echo "Invoice Server - Setup Script"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo -e "${YELLOW}Project directory: $PROJECT_DIR${NC}"

# ------------------------------------------
# 1. Python Virtual Environment
# ------------------------------------------
echo -e "\n${GREEN}[1/5] Setting up Python virtual environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}Dependencies installed!${NC}"

# ------------------------------------------
# 2. PostgreSQL Database
# ------------------------------------------
echo -e "\n${GREEN}[2/5] Setting up PostgreSQL database...${NC}"

DB_NAME="invoice_db"
DB_USER="invoice_user"
DB_PASS="invoice_secure_password_$(date +%s | sha256sum | head -c 16)"

# Check if database exists
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "Database '$DB_NAME' already exists"
else
    echo "Creating database and user..."
    sudo -u postgres psql << EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    echo -e "${GREEN}Database created!${NC}"
    echo -e "${YELLOW}Database password: $DB_PASS${NC}"
fi

# ------------------------------------------
# 3. Environment File
# ------------------------------------------
echo -e "\n${GREEN}[3/5] Setting up environment file...${NC}"

if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Update DATABASE_URL in .env
    sed -i "s|postgresql://invoice_user:your_secure_password@localhost:5432/invoice_db|postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME|g" .env
    
    echo -e "${YELLOW}Created .env file - please update TAX_USERNAME and TAX_PASSWORD!${NC}"
else
    echo ".env file already exists"
fi

# ------------------------------------------
# 4. Create storage directory
# ------------------------------------------
echo -e "\n${GREEN}[4/5] Creating storage directories...${NC}"
mkdir -p storage/captchas storage/invoices

# ------------------------------------------
# 5. Systemd Services
# ------------------------------------------
echo -e "\n${GREEN}[5/5] Installing systemd services...${NC}"

# Update service files with correct paths
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" deploy/invoice-collector.service
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" deploy/invoice-api.service
sed -i "s|Environment=PYTHONPATH=.*|Environment=PYTHONPATH=$PROJECT_DIR|g" deploy/invoice-collector.service
sed -i "s|Environment=PYTHONPATH=.*|Environment=PYTHONPATH=$PROJECT_DIR|g" deploy/invoice-api.service

# Use venv python
sed -i "s|ExecStart=/usr/bin/python3|ExecStart=$PROJECT_DIR/venv/bin/python|g" deploy/invoice-collector.service
sed -i "s|ExecStart=/usr/bin/python3|ExecStart=$PROJECT_DIR/venv/bin/python|g" deploy/invoice-api.service

# Install services
sudo cp deploy/invoice-collector.service /etc/systemd/system/
sudo cp deploy/invoice-collector.timer /etc/systemd/system/
sudo cp deploy/invoice-api.service /etc/systemd/system/

sudo systemctl daemon-reload

echo -e "${GREEN}Systemd services installed!${NC}"

# ------------------------------------------
# Summary
# ------------------------------------------
echo ""
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env file and set TAX_USERNAME and TAX_PASSWORD"
echo "  2. Start API server:    sudo systemctl start invoice-api"
echo "  3. Start collector:     sudo systemctl start invoice-collector.timer"
echo "  4. Check status:        sudo systemctl status invoice-api"
echo ""
echo "Logs:"
echo "  journalctl -u invoice-api -f"
echo "  journalctl -u invoice-collector -f"
echo ""
