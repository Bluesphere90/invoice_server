#!/bin/bash
# =============================================================================
# Invoice Server - Automated Backup Script
# =============================================================================
# This script performs daily backups of:
# - PostgreSQL database (invoice_db)
# - Configuration files (.env)
# - Storage directory (logs, uploaded files)
# 
# Backups are uploaded to OneDrive for disaster recovery.
# 
# Usage: ./backup.sh [backup_dir]
# Default backup directory: ~/backups/invoice_server
# =============================================================================

set -e

# Configuration
PROJECT_DIR="/home/tran-ninh/OtherProjects/invoice_server"
BACKUP_BASE_DIR="${1:-$HOME/backups/invoice_server}"
DB_NAME="invoice_db"
DB_USER="invoice_user"
ONEDRIVE_BACKUP_DIR="Backups/invoice_server"
RETENTION_DAYS=7
ONEDRIVE_RETENTION_COUNT=10
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"
LOG_FILE="$BACKUP_BASE_DIR/backup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_success() {
    log "${GREEN}✅ $1${NC}"
}

log_error() {
    log "${RED}❌ $1${NC}"
}

log_warning() {
    log "${YELLOW}⚠️  $1${NC}"
}

log_info() {
    log "${BLUE}ℹ️  $1${NC}"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_BASE_DIR"

log "=========================================="
log "🚀 INVOICE SERVER BACKUP"
log "=========================================="
log "Project: $PROJECT_DIR"
log "Backup location: $BACKUP_DIR"
log "=========================================="

# =============================================================================
# 1. Backup PostgreSQL Database
# =============================================================================
log "📦 Backing up PostgreSQL database..."
if pg_dump -U "$DB_USER" -h localhost "$DB_NAME" > "$BACKUP_DIR/database.sql" 2>> "$LOG_FILE"; then
    DB_SIZE=$(du -h "$BACKUP_DIR/database.sql" | cut -f1)
    log_success "Database backup completed ($DB_SIZE)"
else
    log_error "Database backup failed!"
    exit 1
fi

# =============================================================================
# 2. Backup Configuration Files
# =============================================================================
log "📄 Backing up configuration files..."

CONFIG_DIR="$BACKUP_DIR/config"
mkdir -p "$CONFIG_DIR"

# Main .env
if [ -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env" "$CONFIG_DIR/.env"
    log_success ".env copied"
else
    log_warning ".env not found"
fi

# Cloudflare tunnel config (if exists)
if [ -f "$PROJECT_DIR/tunnel_config.yml" ]; then
    cp "$PROJECT_DIR/tunnel_config.yml" "$CONFIG_DIR/"
    log_success "tunnel_config.yml copied"
fi

# Systemd service files
if [ -f "$PROJECT_DIR/deploy/invoice-api.service" ]; then
    cp "$PROJECT_DIR/deploy/"*.service "$CONFIG_DIR/" 2>/dev/null || true
    cp "$PROJECT_DIR/deploy/"*.timer "$CONFIG_DIR/" 2>/dev/null || true
    log_success "Service files copied"
fi

# Cloudflare credentials
if [ -d "$HOME/.cloudflared" ]; then
    cp -r "$HOME/.cloudflared" "$CONFIG_DIR/"
    log_success "Cloudflare credentials copied"
fi

# =============================================================================
# 3. Backup Storage Directory (if contains important files)
# =============================================================================
log "📁 Backing up storage directory..."
STORAGE_DIR="$BACKUP_DIR/storage"
mkdir -p "$STORAGE_DIR"

# Only backup specific subdirectories, not logs
if [ -d "$PROJECT_DIR/storage" ]; then
    # Backup any uploaded files or important data (excluding logs)
    find "$PROJECT_DIR/storage" -maxdepth 1 -type f -exec cp {} "$STORAGE_DIR/" \; 2>/dev/null || true
    log_success "Storage files backed up"
fi

# =============================================================================
# 4. Create compressed archive
# =============================================================================
log "🗜️  Creating compressed archive..."
ARCHIVE_NAME="backup_$TIMESTAMP.tar.gz"
cd "$BACKUP_BASE_DIR"
if tar -czf "$ARCHIVE_NAME" "$TIMESTAMP"; then
    ARCHIVE_SIZE=$(du -h "$ARCHIVE_NAME" | cut -f1)
    log_success "Archive created: $ARCHIVE_NAME ($ARCHIVE_SIZE)"
    
    # Create 'latest' symlink
    ln -sf "$ARCHIVE_NAME" "latest.tar.gz"
    log_success "Updated 'latest.tar.gz' symlink"
    
    # Remove uncompressed backup directory
    rm -rf "$TIMESTAMP"
else
    log_error "Failed to create archive!"
    exit 1
fi

# =============================================================================
# 5. Upload to OneDrive
# =============================================================================
log "☁️  Uploading backup to OneDrive..."
if command -v rclone &> /dev/null; then
    if rclone copy "$BACKUP_BASE_DIR/$ARCHIVE_NAME" "onedrive:$ONEDRIVE_BACKUP_DIR/" --progress 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Backup uploaded to OneDrive: $ONEDRIVE_BACKUP_DIR/$ARCHIVE_NAME"
        
        # Cleanup old backups on OneDrive (keep last N)
        log "🧹 Cleaning up old OneDrive backups (keeping last $ONEDRIVE_RETENTION_COUNT)..."
        ONEDRIVE_FILES=$(rclone lsf "onedrive:$ONEDRIVE_BACKUP_DIR/" --files-only 2>/dev/null | grep "^backup_" | sort | head -n -$ONEDRIVE_RETENTION_COUNT)
        if [ -n "$ONEDRIVE_FILES" ]; then
            echo "$ONEDRIVE_FILES" | while read -r file; do
                rclone delete "onedrive:$ONEDRIVE_BACKUP_DIR/$file" 2>/dev/null
                log "Deleted old OneDrive backup: $file"
            done
        fi
    else
        log_warning "OneDrive upload failed! Backup saved locally only."
    fi
else
    log_warning "rclone not installed. Skipping OneDrive upload."
fi

# =============================================================================
# 6. Cleanup old local backups
# =============================================================================
log "🧹 Cleaning up old local backups (older than $RETENTION_DAYS days)..."
DELETED_COUNT=$(find "$BACKUP_BASE_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    log_success "Deleted $DELETED_COUNT old backup(s)"
else
    log "No old backups to delete"
fi

# =============================================================================
# 7. Summary
# =============================================================================
log "=========================================="
log "✅ BACKUP COMPLETED SUCCESSFULLY"
log "=========================================="
log "Archive: $BACKUP_BASE_DIR/$ARCHIVE_NAME"
log "Size: $ARCHIVE_SIZE"
log "OneDrive: onedrive:$ONEDRIVE_BACKUP_DIR/$ARCHIVE_NAME"
log ""
log "To restore from this backup:"
log "  ./scripts/restore.sh $BACKUP_BASE_DIR/$ARCHIVE_NAME"
log "=========================================="

# List current backups
log "Current local backups:"
ls -lh "$BACKUP_BASE_DIR"/*.tar.gz 2>/dev/null | tail -5
