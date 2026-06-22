# Stage 1: Build the React application
FROM node:24-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:stable-alpine

# Copy built static files to Nginx html folder
COPY --from=build /app/dist /usr/share/nginx/html

# Expose Nginx default port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
