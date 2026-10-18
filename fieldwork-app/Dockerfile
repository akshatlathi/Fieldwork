# Fieldwork web (Next.js 16) for Cloud Run. NEXT_PUBLIC_API_BASE is baked in at build time
# from .env.production, which deploy-web.cmd writes before uploading the source.
FROM node:24-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN mkdir -p public && npm run build

FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production PORT=8080 HOSTNAME=0.0.0.0
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
CMD ["node", "server.js"]
