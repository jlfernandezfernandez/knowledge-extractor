FROM node:22-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS runtime

RUN addgroup -S knowli && adduser -S knowli -G knowli
WORKDIR /app
RUN chown knowli:knowli /app
COPY --chown=knowli:knowli --from=dependencies /app/node_modules ./node_modules
COPY --chown=knowli:knowli . .
USER knowli
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
