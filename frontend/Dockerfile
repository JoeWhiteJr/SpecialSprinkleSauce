FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Default API URL for local Docker development; override in docker-compose
ENV NEXT_PUBLIC_API_URL=http://localhost:8000

EXPOSE 3000

# Use dev server for local Docker (hot reload via volume mount).
# For production, switch to: RUN npm run build  +  CMD ["npm", "start"]
CMD ["npm", "run", "dev"]
