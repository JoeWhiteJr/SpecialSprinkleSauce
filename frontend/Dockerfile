FROM node:20.11.1-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Default API URL for local Docker development; override in docker-compose
ENV NEXT_PUBLIC_API_URL=http://localhost:8000

RUN groupadd -r nodejs && useradd -r -g nodejs -m nodejs
USER nodejs

EXPOSE 3000

# Use dev server for local Docker (hot reload via volume mount).
# For production, switch to: RUN npm run build  +  CMD ["npm", "start"]
CMD ["npm", "run", "dev"]
