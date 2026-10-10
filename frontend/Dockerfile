# ==============================================================================
# Multi-Stage Frontend Dockerfile
# Central Attendance Management System (React + Vite + TypeScript)
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Stage (Node.js)
# ------------------------------------------------------------------------------
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency specifications first for layer caching
COPY package.json package-lock.json ./

# Deterministic dependency installation
RUN npm ci

# Copy project source and configuration files
COPY . .

# Compile TypeScript and build production bundle
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Stage (Nginx Alpine)
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runner

# Remove default static content and configuration
RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled production artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/healthz || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
