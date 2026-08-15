# Single stage: this is a local-only demo service (see README's locked deployment
# scope), so a leaner nginx-based static-serve image isn't worth the extra config.
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 4173

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "4173"]
