FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
ARG NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE=UTC
ARG NEXT_PUBLIC_DISPLAY_TIMEZONE=Europe/Moscow
ARG NEXT_PUBLIC_DATETIME_LOCALE=ru-RU

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE=$NEXT_PUBLIC_API_TIMESTAMP_TIMEZONE \
    NEXT_PUBLIC_DISPLAY_TIMEZONE=$NEXT_PUBLIC_DISPLAY_TIMEZONE \
    NEXT_PUBLIC_DATETIME_LOCALE=$NEXT_PUBLIC_DATETIME_LOCALE

RUN npm run build && npm prune --omit=dev

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/package.json ./
COPY --from=builder /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "run", "start"]
