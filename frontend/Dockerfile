# frontend/Dockerfile

# Stage 1: Build the Angular application
FROM node:18-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve the application from Nginx
FROM nginx:alpine

# Copy the build output to replace the default Nginx web server files
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

# Copy a basic Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
