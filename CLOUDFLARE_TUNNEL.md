# Cloudflare Tunnel Setup Guide

Hướng dẫn cấu hình Cloudflare Tunnel để expose Invoice API ra internet.

## Prerequisites

- Tài khoản Cloudflare (miễn phí)
- Domain đã thêm vào Cloudflare

## Cài Đặt Cloudflared

```bash
# Download và cài đặt
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Đăng nhập Cloudflare
cloudflared tunnel login
```

## Tạo Tunnel

```bash
# Tạo tunnel mới
cloudflared tunnel create invoice-api

# Cấu hình routing
cloudflared tunnel route dns invoice-api api.yourdomain.com
```

## Cấu Hình

Tạo file `/etc/cloudflared/config.yml`:

```yaml
tunnel: invoice-api
credentials-file: /home/tran-ninh/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

## Chạy Service

```bash
# Cài đặt systemd service
sudo cloudflared service install

# Khởi động
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Kiểm tra
sudo systemctl status cloudflared
```

## Test

```bash
curl https://api.yourdomain.com/api/health
```
