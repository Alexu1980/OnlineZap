FROM node:20-alpine AS builder

WORKDIR /build

# Копируем package.json и устанавливаем зависимости
COPY app/package.json ./package.json
RUN npm install

# Копируем весь исходный код
COPY app/ ./

# Собираем проект
RUN npm run build

# Финальный образ с nginx
FROM nginx:alpine

# Копируем собранные файлы
COPY --from=builder /build/dist /usr/share/nginx/html

# Копируем конфигурацию nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
