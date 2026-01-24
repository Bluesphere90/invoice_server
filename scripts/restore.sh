#!/bin/bash
# =============================================================================
# Invoice Server - Restore Script
# =============================================================================
# This script restores from a backup archive created by backup.sh
# 
# Usage: 
#   ./restore.sh <backup_archive.tar.gz>
#   ./restore.sh <backup_archive.tar.gz> --dry-run    # Preview only
#   ./restore.sh --download-latest                    # Download from OneDrive
# 
# =============================================================================

set -e

# Configuration
PROJECT_DIR="/home/tran-ninh/OtherProjects/invoice_server"
DB_NAME="invoice_db"
DB_USER="invoice_user"
ONEDRIVE_BACKUP_DIR="Backups/invoice_server"
RESTORE_TEMP_DIR="/tmp/invoice_server_restore_$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
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

# Cleanup function
cleanup() {
    if [ -d "$RESTORE_TEMP_DIR" ]; then
        rm -rf "$RESTORE_TEMP_DIR"
    fi
}
trap cleanup EXIT

# Usage function
usage() {
    echo "Usage: $0 <backup_archive.tar.gz> [options]"
    echo ""
    echo "Options:"
    echo "  --dry-run           Preview what will be restored without making changes"
    echo "  --download-latest   Download latest backup from OneDrive first"
    echo "  --db-only           Restore database only"
    echo "  --config-only       Restore configuration only"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/backup_20260124_030000.tar.gz"
    echo "  $0 --download-latest"
    echo "  $0 /path/to/backup.tar.gz --dry-run"
    exit 1
}

# Parse arguments
DRY_RUN=false
DOWNLOAD_LATEST=false
DB_ONLY=false
CONFIG_ONLY=false
BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --download-latest)
            DOWNLOAD_LATEST=true
            shift
            ;;
        --db-only)
            DB_ONLY=true
            shift
            ;;
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Download latest from OneDrive if requested
if [ "$DOWNLOAD_LATEST" = true ]; then
    log_info "Downloading latest backup from OneDrive..."
    mkdir -p "$RESTORE_TEMP_DIR"
    
    # Get latest backup file name
    LATEST_BACKUP=$(rclone lsf "onedrive:$ONEDRIVE_BACKUP_DIR/" --files-only 2>/dev/null | grep "^backup_" | sort | tail -1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup found on OneDrive!"
        exit 1
    fi
    
    log_info "Found latest backup: $LATEST_BACKUP"
    
    if rclone copy "onedrive:$ONEDRIVE_BACKUP_DIR/$LATEST_BACKUP" "$RESTORE_TEMP_DIR/" --progress; then
        BACKUP_FILE="$RESTORE_TEMP_DIR/$LATEST_BACKUP"
        log_success "Downloaded: $BACKUP_FILE"
    else
        log_error "Failed to download backup from OneDrive!"
        exit 1
    fi
fi

# Validate backup file
if [ -z "$BACKUP_FILE" ]; then
    log_error "No backup file specified!"
    usage
fi

if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

log "=========================================="
log "🔄 INVOICE SERVER RESTORE"
log "=========================================="
log "Backup file: $BACKUP_FILE"
log "Project dir: $PROJECT_DIR"
log "=========================================="

if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN MODE - No changes will be made"
fi

# Extract backup
log "📦 Extracting backup archive..."
mkdir -p "$RESTORE_TEMP_DIR"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_TEMP_DIR"

# Find the extracted directory
EXTRACTED_DIR=$(find "$RESTORE_TEMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -1)

if [ -z "$EXTRACTED_DIR" ]; then
    log_error "Failed to extract backup!"
    exit 1
fi

log_success "Extracted to: $EXTRACTED_DIR"

# Show contents
log_info "Backup contents:"
ls -la "$EXTRACTED_DIR"

# =============================================================================
# Restore Database
# =============================================================================
if [ "$CONFIG_ONLY" = false ] && [ -f "$EXTRACTED_DIR/database.sql" ]; then
    log "📊 Restoring database..."
    DB_SIZE=$(du -h "$EXTRACTED_DIR/database.sql" | cut -f1)
    log_info "Database dump size: $DB_SIZE"
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would restore database from: $EXTRACTED_DIR/database.sql"
    else
        # Create backup of current database first
        log_info "Creating backup of current database..."
        CURRENT_BACKUP="/tmp/invoice_db_pre_restore_$(date +%Y%m%d_%H%M%S).sql"
        pg_dump -U "$DB_USER" -h localhost "$DB_NAME" > "$CURRENT_BACKUP" 2>/dev/null || true
        
        # Restore database
        log_warning "This will REPLACE all data in $DB_NAME database!"
        read -p "Continue? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            # Drop and recreate database
            psql -U "$DB_USER" -h localhost -c "DROP DATABASE IF EXISTS ${DB_NAME}_restore;" postgres 2>/dev/null || true
            psql -U "$DB_USER" -h localhost -c "CREATE DATABASE ${DB_NAME}_restore OWNER $DB_USER;" postgres
            
            if psql -U "$DB_USER" -h localhost "${DB_NAME}_restore" < "$EXTRACTED_DIR/database.sql"; then
                # Swap databases
                psql -U "$DB_USER" -h localhost -c "DROP DATABASE IF EXISTS ${DB_NAME}_old;" postgres 2>/dev/null || true
                psql -U "$DB_USER" -h localhost -c "ALTER DATABASE $DB_NAME RENAME TO ${DB_NAME}_old;" postgres
                psql -U "$DB_USER" -h localhost -c "ALTER DATABASE ${DB_NAME}_restore RENAME TO $DB_NAME;" postgres
                log_success "Database restored successfully!"
                log_info "Old database saved as: ${DB_NAME}_old"
            else
                log_error "Database restore failed!"
                psql -U "$DB_USER" -h localhost -c "DROP DATABASE IF EXISTS ${DB_NAME}_restore;" postgres 2>/dev/null || true
                exit 1
            fi
        else
            log_warning "Database restore skipped by user"
        fi
    fi
else
    if [ "$CONFIG_ONLY" = false ]; then
        log_warning "No database.sql found in backup"
    fi
fi

# =============================================================================
# Restore Configuration
# =============================================================================
if [ "$DB_ONLY" = false ] && [ -d "$EXTRACTED_DIR/config" ]; then
    log "📄 Restoring configuration files..."
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would restore config files:"
        ls -la "$EXTRACTED_DIR/config"
    else
        # Restore .env
        if [ -f "$EXTRACTED_DIR/config/.env" ]; then
            if [ -f "$PROJECT_DIR/.env" ]; then
                cp "$PROJECT_DIR/.env" "$PROJECT_DIR/.env.bak"
                log_info "Backed up current .env to .env.bak"
            fi
            cp "$EXTRACTED_DIR/config/.env" "$PROJECT_DIR/.env"
            log_success ".env restored"
        fi
        
        # Restore tunnel config
        if [ -f "$EXTRACTED_DIR/config/tunnel_config.yml" ]; then
            cp "$EXTRACTED_DIR/config/tunnel_config.yml" "$PROJECT_DIR/"
            log_success "tunnel_config.yml restored"
        fi
        
        # Restore Cloudflare credentials
        if [ -d "$EXTRACTED_DIR/config/.cloudflared" ]; then
            cp -r "$EXTRACTED_DIR/config/.cloudflared" "$HOME/"
            log_success "Cloudflare credentials restored"
        fi
    fi
else
    if [ "$DB_ONLY" = false ]; then
        log_warning "No config directory found in backup"
    fi
fi

# =============================================================================
# Restore Storage
# =============================================================================
if [ "$DB_ONLY" = false ] && [ "$CONFIG_ONLY" = false ] && [ -d "$EXTRACTED_DIR/storage" ]; then
    log "📁 Restoring storage files..."
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "[DRY RUN] Would restore storage files:"
        ls -la "$EXTRACTED_DIR/storage"
    else
        mkdir -p "$PROJECT_DIR/storage"
        cp -r "$EXTRACTED_DIR/storage"/* "$PROJECT_DIR/storage/" 2>/dev/null || true
        log_success "Storage files restored"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
log "=========================================="
if [ "$DRY_RUN" = true ]; then
    log "🔍 DRY RUN COMPLETED"
    log "No changes were made. Run without --dry-run to apply changes."
else
    log "✅ RESTORE COMPLETED"
    log ""
    log "Next steps:"
    log "  1. Review restored configuration files"
    log "  2. Restart services: sudo systemctl restart invoice-api"
    log "  3. Verify application is working correctly"
fi
log "=========================================="
