# Hướng Dẫn Khôi Phục Hệ Thống Invoice Server

Tài liệu này hướng dẫn cách khôi phục hệ thống Invoice Server khi máy chủ bị hỏng hoặc cần migrate sang server mới.

---

## 📋 Thông Tin Backup

| Item | Value |
|------|-------|
| Vị trí Backup Local | `/home/tran-ninh/backups/invoice_server/` |
| Vị trí OneDrive | `Backups/invoice_server/` |
| Tần suất | Hàng ngày lúc 3:00 AM |
| Nội dung | Database PostgreSQL, file `.env`, cấu hình |

---

## 🚀 Khôi Phục Nhanh (Quick Recovery)

Nếu bạn đang trên máy chủ CÓ SẴN cấu hình rclone:

```bash
cd /home/tran-ninh/OtherProjects/invoice_server
./scripts/restore.sh --download-latest
```

---

## 📥 Tải Backup Từ OneDrive

### Cách 1: Sử dụng rclone (nếu đã cài)

```bash
# Liệt kê các backup có sẵn
rclone lsf onedrive:Backups/invoice_server/

# Tải backup mới nhất
rclone copy onedrive:Backups/invoice_server/backup_YYYYMMDD_HHMMSS.tar.gz ./
```

### Cách 2: Tải thủ công từ OneDrive

1. Truy cập: https://onedrive.live.com/
2. Đăng nhập tài khoản Microsoft
3. Điều hướng đến: `Backups/invoice_server/`
4. Tải file backup mới nhất (ví dụ: `backup_20260124_030000.tar.gz`)

---

## 🔧 Khôi Phục Trên Máy Chủ Mới

### Bước 1: Cài đặt môi trường

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Cài đặt Python
sudo apt install python3 python3-pip python3-venv -y

# Cài đặt Node.js (cho frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Cài đặt rclone (để tải backup từ OneDrive)
curl https://rclone.org/install.sh | sudo bash
```

### Bước 2: Cấu hình rclone để kết nối OneDrive

```bash
rclone config

# Làm theo hướng dẫn:
# 1. Chọn "n" (new remote)
# 2. Đặt tên: onedrive
# 3. Chọn số tương ứng với "Microsoft OneDrive"
# 4. Để trống client_id và client_secret
# 5. Chọn "1" (OneDrive Personal)
# 6. Làm theo OAuth flow trên trình duyệt
```

### Bước 3: Tải và giải nén backup

```bash
# Tạo thư mục project
mkdir -p /home/tran-ninh/OtherProjects/invoice_server
cd /home/tran-ninh/OtherProjects/invoice_server

# Tải backup mới nhất
LATEST=$(rclone lsf onedrive:Backups/invoice_server/ --files-only | sort | tail -1)
rclone copy "onedrive:Backups/invoice_server/$LATEST" /tmp/

# Giải nén
tar -xzf /tmp/$LATEST -C /tmp/
EXTRACTED_DIR=$(ls -d /tmp/2026*/)
```

### Bước 4: Khôi phục Database

```bash
# Tạo user PostgreSQL
sudo -u postgres psql -c "CREATE USER invoice_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE invoice_db OWNER invoice_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE invoice_db TO invoice_user;"

# Khôi phục data
psql -U invoice_user -h localhost invoice_db < $EXTRACTED_DIR/database.sql
```

### Bước 5: Khôi phục Code và Cấu hình

```bash
# Clone repository (hoặc copy source code)
git clone https://github.com/your-repo/invoice_server.git .

# Khôi phục file .env
cp $EXTRACTED_DIR/config/.env /home/tran-ninh/OtherProjects/invoice_server/.env

# Cập nhật DATABASE_URL trong .env nếu password đã thay đổi
nano .env

# Tạo virtual environment và cài đặt dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Bước 6: Khôi phục Frontend

```bash
cd frontend
npm install
npm run build
```

### Bước 7: Cấu hình Systemd Services

```bash
# Copy service files
sudo cp deploy/*.service /etc/systemd/system/
sudo cp deploy/*.timer /etc/systemd/system/

# Reload và start services
sudo systemctl daemon-reload
sudo systemctl enable invoice-api
sudo systemctl start invoice-api

# Kiểm tra status
sudo systemctl status invoice-api
```

### Bước 8: Cấu hình Cloudflare Tunnel (nếu sử dụng)

```bash
# Khôi phục credentials
cp -r $EXTRACTED_DIR/config/.cloudflared ~/.cloudflared/

# Khôi phục tunnel config
cp $EXTRACTED_DIR/config/tunnel_config.yml ./

# Chạy tunnel
cloudflared tunnel run
```

---

## ✅ Xác Nhận Hoạt Động

```bash
# Kiểm tra API
curl http://localhost:8000/api/health

# Kiểm tra database
psql -U invoice_user -h localhost invoice_db -c "SELECT COUNT(*) FROM users;"

# Kiểm tra logs
journalctl -u invoice-api -f
```

---

## 🆘 Xử Lý Sự Cố

### Lỗi kết nối Database

```bash
# Kiểm tra PostgreSQL đang chạy
sudo systemctl status postgresql

# Kiểm tra cấu hình pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Đảm bảo có dòng: local all invoice_user md5
```

### Lỗi thiếu dependencies Python

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Lỗi rclone không kết nối được OneDrive

```bash
# Xóa và cấu hình lại
rclone config delete onedrive
rclone config
```

---

## 📞 Liên Hệ

Nếu cần hỗ trợ, liên hệ quản trị viên hệ thống.
