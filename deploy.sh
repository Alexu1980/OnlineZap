#!/bin/bash

# ============================================
# Скрипт развёртывания OnlineZap на сервере
# ============================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  OnlineZap Deployment Script${NC}"
echo -e "${GREEN}============================================${NC}"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ошибка: этот скрипт должен запускаться от root${NC}"
    exit 1
fi

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker не установлен. Установка...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}Docker установлен${NC}"
else
    echo -e "${GREEN}Docker уже установлен: $(docker --version)${NC}"
fi

# Проверка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose не установлен. Установка...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose установлен${NC}"
else
    echo -e "${GREEN}Docker Compose уже установлен: $(docker-compose --version)${NC}"
fi

# Установка Certbot для SSL (опционально)
install_certbot() {
    echo -e "${YELLOW}Установка Certbot для SSL сертификатов...${NC}"
    if command -v apt &> /dev/null; then
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    elif command -v yum &> /dev/null; then
        yum install -y certbot python3-certbot-nginx
    fi
    echo -e "${GREEN}Certbot установлен${NC}"
}

# Настройка SSL
setup_ssl() {
    read -p "Хотите настроить SSL сертификат? (y/n): " use_ssl
    
    if [ "$use_ssl" = "y" ] || [ "$use_ssl" = "Y" ]; then
        read -p "Введите доменное имя (например, example.com): " domain
        read -p "Введите email для Certbot: " email
        
        # Создаём конфигурацию Nginx с SSL
        cat > nginx/conf.d/default.conf <<EOF
server {
    listen 80;
    server_name ${domain};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${domain};

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 10M;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /app/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        location /app/assets/ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    location /api/health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location / {
        return 301 /app;
    }
}
EOF

        # Получаем SSL сертификат
        mkdir -p nginx/ssl
        certbot certonly --standalone -d ${domain} -m ${email} --agree-tos --non-interactive
        cp /etc/letsencrypt/live/${domain}/fullchain.pem nginx/ssl/cert.pem
        cp /etc/letsencrypt/live/${domain}/privkey.pem nginx/ssl/key.pem
        chmod 600 nginx/ssl/key.pem
        
        echo -e "${GREEN}SSL сертификат получен для ${domain}${NC}"
    fi
}

# Копирование credentials.json
copy_credentials() {
    if [ ! -f credentials.json ]; then
        echo -e "${YELLOW}Файл credentials.json не найден в текущей директории.${NC}"
        echo -e "${YELLOW}Пожалуйста, скопируйте файл credentials.json в эту директорию перед запуском.${NC}"
        read -p "Продолжить без credentials.json? (y/n): " skip_creds
        
        if [ "$skip_creds" != "y" ] && [ "$skip_creds" != "Y" ]; then
            exit 1
        fi
    else
        echo -e "${GREEN}credentials.json найден${NC}"
    fi
}

# Настройка firewall
setup_firewall() {
    echo -e "${YELLOW}Настройка firewall...${NC}"
    
    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
        echo -e "${GREEN}UFW настроен${NC}"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --reload
        echo -e "${GREEN}firewalld настроен${NC}"
    else
        echo -e "${YELLOW}Firewall не обнаружен. Настройте вручную.${NC}"
    fi
}

# Основная функция развёртывания
deploy() {
    echo -e "${GREEN}Начало развёртывания...${NC}"
    
    # Копируем credentials.json
    copy_credentials
    
    # Настраиваем SSL (опционально)
    setup_ssl
    
    # Настраиваем firewall
    setup_firewall
    
    # Копируем .env
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Создание .env из .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}Пожалуйста, отредактируйте .env перед запуском${NC}"
        read -p "Нажмите Enter для продолжения..."
    fi
    
    # Останавливаем старые контейнеры
    echo -e "${YELLOW}Остановка старых контейнеров...${NC}"
    docker-compose down
    
    # Собираем и запускаем
    echo -e "${GREEN}Сборка и запуск контейнеров...${NC}"
    docker-compose build --no-cache
    docker-compose up -d
    
    # Проверка статуса
    echo -e "${GREEN}Ожидание запуска сервисов...${NC}"
    sleep 10
    
    docker-compose ps
    
    # Проверка health check
    if docker inspect --format='{{.State.Health.Status}}' onlinezap-app | grep -q "healthy"; then
        echo -e "${GREEN}✅ Приложение успешно запущено!${NC}"
        echo -e "${GREEN}MiniApp доступен по адресу: http://localhost:8000/app${NC}"
        echo -e "${GREEN}API доступен по адресу: http://localhost:8000/api${NC}"
    else
        echo -e "${YELLOW}⚠️  Приложение запущено, но health check не прошёл.${NC}"
        echo -e "${YELLOW}Проверьте логи: docker-compose logs app${NC}"
    fi
}

# Остановка сервиса
stop() {
    echo -e "${YELLOW}Остановка сервиса...${NC}"
    docker-compose down
    echo -e "${GREEN}Сервис остановлен${NC}"
}

# Перезапуск сервиса
restart() {
    echo -e "${YELLOW}Перезапуск сервиса...${NC}"
    docker-compose down
    docker-compose up -d
    echo -e "${GREEN}Сервис перезапущен${NC}"
}

# Просмотр логов
logs() {
    docker-compose logs -f app
}

# Очистка (удаление контейнеров и томов)
clean() {
    echo -e "${RED}⚠️  Очистка удалит все контейнеры и данные!${NC}"
    read -p "Продолжить? (y/n): " confirm
    
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker-compose down -v
        docker system prune -f
        echo -e "${GREEN}Очистка выполнена${NC}"
    fi
}

# Главный меню
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    clean)
        clean
        ;;
    help)
        echo "Использование: $0 {deploy|stop|restart|logs|clean|help}"
        echo ""
        echo "Команды:"
        echo "  deploy   - Развернуть приложение (по умолчанию)"
        echo "  stop     - Остановить приложение"
        echo "  restart  - Перезапустить приложение"
        echo "  logs     - Просмотр логов"
        echo "  clean    - Очистка (удаление контейнеров и данных)"
        echo "  help     - Показать эту справку"
        ;;
    *)
        echo "Неизвестная команда: $1"
        echo "Используйте $0 help для справки"
        exit 1
        ;;
esac
