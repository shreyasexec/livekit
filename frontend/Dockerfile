FROM node:20-alpine

WORKDIR /app

# Install OpenSSL for certificate generation
RUN apk add --no-cache openssl

# Generate self-signed SSL certificate
RUN mkdir -p /etc/ssl/private /etc/ssl/certs && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/localhost-key.pem \
    -out /etc/ssl/certs/localhost.pem \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:192.168.20.62"

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host"]
