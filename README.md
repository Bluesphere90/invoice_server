# Invoice Server

Hệ thống tự động tải và quản lý hóa đơn điện tử từ cổng Tổng Cục Thuế Việt Nam.

## Cấu Trúc Dự Án

```
invoice_server/
├── backend/
│   ├── collector/      # Service tải hóa đơn
│   ├── api/            # FastAPI REST server
│   ├── database/       # PostgreSQL layer
│   └── config/         # Configuration
├── frontend/           # Web UI (Vite + React)
├── deploy/             # Systemd services
├── migrations/         # Database migrations
└── storage/            # Runtime data
```

## Quick Start

### 1. Cài đặt tự động
```bash
cd deploy
./setup.sh
```

### 2. Cấu hình credentials
```bash
nano .env
# Cập nhật TAX_USERNAME và TAX_PASSWORD
```

### 3. Chạy services
```bash
# API server
sudo systemctl start invoice-api
sudo systemctl enable invoice-api

# Collector (chạy định kỳ)
sudo systemctl start invoice-collector.timer
sudo systemctl enable invoice-collector.timer
```

### 4. Kiểm tra
```bash
curl http://localhost:8000/api/health
```

## Cloudflare Tunnel

Xem hướng dẫn chi tiết tại: [CLOUDFLARE_TUNNEL.md](./CLOUDFLARE_TUNNEL.md)

## Development

```bash
# Activate virtual environment
source venv/bin/activate

# Run collector manually
python -m backend.collector.main

# Run API server
uvicorn backend.api.main:app --reload
```
