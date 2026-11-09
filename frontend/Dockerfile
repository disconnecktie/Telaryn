# Build Telaryn once, then serve its static assets through an unprivileged gateway.
FROM node:22-alpine AS build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./

ARG VITE_API_URL=/api
ARG TELARYN_BUILD=development
ENV VITE_API_URL=$VITE_API_URL
ENV TELARYN_BUILD=$TELARYN_BUILD

RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine

ENV ATLAS_BACKEND_ORIGIN=http://backend:8000 \
    NGINX_ENVSUBST_FILTER=ATLAS_BACKEND_ORIGIN

COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /frontend/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
