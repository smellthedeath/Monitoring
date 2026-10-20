#!/bin/bash
# ==============================================================================
# Automated Monitoring Stack Backup Script
# Creates compressed daily tarball of configs, rules, dashboards, and SQLite DB.
# Retains the last 14 days of backups automatically.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/root/monitor/backup/daily}"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup-${TIMESTAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"

echo "Creating monitoring backup at ${BACKUP_FILE} ..."

tar -czf "${BACKUP_FILE}" \
  -C / \
  etc/prometheus \
  etc/alertmanager \
  etc/nginx \
  root/monitor/docker-compose.yml \
  root/monitor/grafana/provisioning \
  var/lib/docker/volumes/monitor_grafana_data/_data/grafana.db \
  2>/dev/null || true

if [ -f "${BACKUP_FILE}" ]; then
  FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
  echo "Backup created successfully: ${FILE_SIZE}"
else
  echo "Error: Backup failed to create!" >&2
  exit 1
fi

# Retention cleanup: delete backups older than 14 days
find "${BACKUP_DIR}" -name "backup-*.tar.gz" -mtime +14 -delete
echo "Retention cleanup complete."
