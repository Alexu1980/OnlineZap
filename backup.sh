#!/bin/bash

# ============================================
# Скрипт резервного копирования базы данных
# ============================================

set -e

# Настройки
BACKUP_DIR="/opt/onlinezap/backups"
CONTAINER_NAME="onlinezap-app"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/bookings_$TIMESTAMP.db"
RETENTION_DAYS=30

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

echo "[$(date)] Начало резервного копирования..."

# Копирование базы данных из контейнера
docker cp $CONTAINER_NAME:/app/Data/bookings.db $BACKUP_FILE

# Сжатие
gzip $BACKUP_FILE

# Удаление старых бэкапов
find $BACKUP_DIR -name "bookings_*.db.gz" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Бэкап создан: $BACKUP_FILE.gz"
echo "[$(date)] Старые бэкапы старше $RETENTION_DAYS дней удалены"
