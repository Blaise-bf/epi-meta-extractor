#!/bin/bash
# =================================================================
# SSL Certificate Setup Script for Let's Encrypt
# =================================================================
# Run this on your Digital Ocean droplet to obtain and configure
# SSL certificates using Certbot.
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - Domain DNS pointing to your droplet IP
#   - docker-compose.prod.yml and nginx/ configured
#
# Usage:
#   chmod +x scripts/setup-ssl.sh
#   ./scripts/setup-ssl.sh your-domain.com
# =================================================================

set -e

DOMAIN=${1:-}
EMAIL=${2:-your-email@example.com}

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> [email]"
    echo "Example: $0 epimeta.example.com admin@example.com"
    exit 1
fi

echo "Setting up SSL for domain: $DOMAIN"

# Create directories
mkdir -p nginx/ssl
mkdir -p nginx/certbot-data/www
mkdir -p nginx/certbot-data/conf

# -----------------------------------------------------------------
# Step 1: Obtain certificates with Certbot standalone
# -----------------------------------------------------------------
echo "Obtaining SSL certificate from Let's Encrypt..."

docker run -it --rm \
    -v "$(pwd)/nginx/certbot-data/conf:/etc/letsencrypt" \
    -v "$(pwd)/nginx/certbot-data/www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --preferred-challenges http \
    -d "$DOMAIN" \
    --agree-tos \
    --non-interactive \
    --email "$EMAIL"

# -----------------------------------------------------------------
# Step 2: Copy certificates to nginx/ssl
# -----------------------------------------------------------------
echo "Copying certificates..."

cp "nginx/certbot-data/conf/live/$DOMAIN/fullchain.pem" nginx/ssl/
cp "nginx/certbot-data/conf/live/$DOMAIN/privkey.pem" nginx/ssl/

# -----------------------------------------------------------------
# Step 3: Create renewal hook
# -----------------------------------------------------------------
echo "Creating renewal hook..."

cat > scripts/renew-ssl.sh << 'EOF'
#!/bin/bash
# Auto-renewal hook for Let's Encrypt certificates
# Run via cron: 0 3 * * * /path/to/scripts/renew-ssl.sh

cd "$(dirname "$0")/.." || exit 1

docker run -it --rm \
    -v "$(pwd)/nginx/certbot-data/conf:/etc/letsencrypt" \
    -v "$(pwd)/nginx/certbot-data/www:/var/www/certbot" \
    -p 80:80 \
    certbot/certbot renew \
    --quiet

# Reload nginx to pick up new certificates
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
EOF

chmod +x scripts/renew-ssl.sh

echo ""
echo "SSL setup complete!"
echo "Certificates are in: nginx/ssl/"
echo ""
echo "To auto-renew, add this to your crontab:"
echo "  0 3 * * * $(pwd)/scripts/renew-ssl.sh"
echo ""
echo "You can now start the application with:"
echo "  docker compose -f docker-compose.prod.yml up -d"
