#!/bin/bash

# Configuration
DB_NAME=${DB_NAME:-"daftarcash_db"}
DB_USER=${DB_USER:-"postgres"}
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
BACKUP_DIR="/var/backups/daftarcash"
KEEP_DAYS=7

# Load environment variables if .env file exists in the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(cat "${SCRIPT_DIR}/.env" | grep -v '#' | xargs)
fi

# Date format for backup file
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${DATE}.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "Starting database backup for ${DB_NAME} at $(date)..."

# Export password for non-interactive pg_dump if present
if [ -n "${DB_PASSWORD}" ]; then
    export PGPASSWORD="${DB_PASSWORD}"
fi

# Run pg_dump and compress the output using gzip
pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully: ${BACKUP_FILE}"
    
    # =========================================================================
    # OPTIONAL AWS S3 UPLOAD CONFIGURATION
    # To enable S3 uploads:
    # 1. Ensure the AWS CLI is installed on the server.
    # 2. Configure AWS credentials via 'aws configure'.
    # 3. Uncomment the lines below and set your S3_BUCKET name.
    # =========================================================================
    # S3_BUCKET="your-s3-bucket-name"
    # echo "Uploading backup to S3..."
    # aws s3 cp "${BACKUP_FILE}" "s3://${S3_BUCKET}/backups/$(basename "${BACKUP_FILE}")"
    # if [ $? -eq 0 ]; then
    #     echo "Uploaded to S3 successfully."
    # else
    #     echo "S3 Upload failed."
    # fi
    # =========================================================================
    
else
    echo "Error: Database backup failed."
    exit 1
fi

# Delete backups older than KEEP_DAYS days locally to save disk space
echo "Cleaning up local backups older than ${KEEP_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "${DB_NAME}_backup_*.sql.gz" -mtime +${KEEP_DAYS} -delete

echo "Backup process finished at $(date)."
