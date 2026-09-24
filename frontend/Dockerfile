# ---------- Frontend Dockerfile (multi-stage) ----------
FROM node:20-alpine AS base
WORKDIR /app

# ---------- Development stage ----------
FROM base AS dev
ENV NODE_ENV=development
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ---------- Build stage ----------
FROM base AS build
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# ---------- Production stage ----------
FROM node:20-alpine AS prod
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["npm", "run", "start"]