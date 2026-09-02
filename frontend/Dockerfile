# === Стадия установки зависимостей и сборки ===
FROM node:22-alpine AS builder
WORKDIR /app

# Включаем corepack, чтобы использовать pnpm без глобальной установки
RUN corepack enable && corepack prepare pnpm@11.13.1 --activate

# Контекст сборки — корень репозитория, поэтому пути с префиксом frontend/
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY frontend/. .
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm run build

# === Runtime-стадия: раздача статики через nginx ===
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY deploy/nginx/frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1
