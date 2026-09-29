# PowerShell скрипт для развёртывания на Windows Server
# Запустите от имени администратора

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Green
Write-Host "  OnlineZap Windows Deployment Script" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

# Проверка прав администратора
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Ошибка: скрипт должен запускаться от имени администратора" -ForegroundColor Red
    exit 1
}

# Проверка Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker не установлен. Установка через Chocolatey..." -ForegroundColor Yellow
    
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }
    
    choco install docker-desktop -y
    Write-Host "Docker установлен" -ForegroundColor Green
} else {
    Write-Host "Docker уже установлен: $(docker --version)" -ForegroundColor Green
}

# Проверка Docker Compose
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Compose не установлен. Проверка Docker Desktop..." -ForegroundColor Yellow
    Write-Host "Убедитесь, что Docker Desktop запущен" -ForegroundColor Yellow
} else {
    Write-Host "Docker Compose уже установлен: $(docker-compose --version)" -ForegroundColor Green
}

# Копирование .env
if (-not (Test-Path .env)) {
    Write-Host "Создание .env из .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Пожалуйста, отредактируйте .env перед запуском" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для продолжения"
}

# Остановка старых контейнеров
Write-Host "Остановка старых контейнеров..." -ForegroundColor Yellow
docker-compose down

# Сборка и запуск
Write-Host "Сборка и запуск контейнеров..." -ForegroundColor Green
docker-compose up -d --build

# Ожидание запуска
Write-Host "Ожидание запуска сервисов..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Проверка статуса
docker-compose ps

# Проверка health
$health = docker inspect --format='{{.State.Health.Status}}' onlinezap-app 2>$null
if ($health -eq "healthy") {
    Write-Host "✅ Приложение успешно запущено!" -ForegroundColor Green
    Write-Host "MiniApp доступен по адресу: http://localhost:8000/app" -ForegroundColor Green
    Write-Host "API доступен по адресу: http://localhost:8000/api" -ForegroundColor Green
} else {
    Write-Host "⚠️  Приложение запущено, но health check не прошёл." -ForegroundColor Yellow
    Write-Host "Проверьте логи: docker-compose logs app" -ForegroundColor Yellow
}
