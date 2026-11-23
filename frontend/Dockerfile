FROM node:24-alpine AS build
WORKDIR /srv/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
ARG BACKEND_URL=http://api:8001
ENV BACKEND_URL=$BACKEND_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build
FROM node:24-alpine
WORKDIR /srv/frontend
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 BACKEND_URL=http://api:8001
COPY --from=build --chown=node:node /srv/frontend ./
USER node
EXPOSE 3000
CMD ["npm","run","start","--","--hostname","0.0.0.0"]
