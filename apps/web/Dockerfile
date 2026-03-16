FROM node:18-alpine AS deps
WORKDIR /app/apps/web
COPY apps/web/package.json ./
RUN npm install

FROM node:18-alpine AS builder
WORKDIR /app/apps/web
COPY --from=deps /app/apps/web/node_modules ./node_modules
COPY apps/web ./
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app/apps/web
ENV NODE_ENV=production
COPY --from=builder /app/apps/web ./
EXPOSE 3000
CMD ["npm", "start"]