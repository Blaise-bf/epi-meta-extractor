# Deploying Epi Meta Extractor to Digital Ocean

This guide walks you through deploying the **Epi Meta Extractor** application to a **Digital Ocean Droplet** (or any Docker-enabled VPS) using Docker Compose.

---

## Prerequisites

- A Digital Ocean account
- A domain name (optional but recommended for SSL)
- Docker and Docker Compose installed on your droplet
- SSH access to your droplet

---

## Step 1: Provision a Droplet

1. Log in to [Digital Ocean](https://cloud.digitalocean.com)
2. Create a new Droplet with:
   - **OS**: Ubuntu 24.04 (LTS)
   - **Plan**: Basic (at least 2 vCPUs / 4 GB RAM recommended for LLM workloads)
   - **Region**: Closest to your users
   - **SSH Key**: Add your SSH key for secure access
3. Note the droplet's public IP address

---

## Step 2: Point Your Domain (Optional)

If using a custom domain:

1. In your DNS provider, create an **A record** pointing your domain to the droplet IP
2. Wait for DNS propagation (can take a few minutes to hours)

---

## Step 3: Install Docker on the Droplet

SSH into your droplet and run:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
sudo apt install docker-compose-plugin

# Verify
docker --version
docker compose version
```

---

## Step 4: Clone the Repository

```bash
git clone https://github.com/Blaise-bf/epi-meta-extractor.git
cd epi-meta-extractor
```

---

## Step 5: Configure Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` with your production values:

```bash
nano .env
```

**Critical values to set:**

| Variable | Description |
|----------|-------------|
| `DOMAIN` | Your domain or droplet IP |
| `FRONTEND_ORIGIN` | Full public URL (`https://your-domain.com`) |
| `NEXT_PUBLIC_API_URL` | Public API URL (`https://your-domain.com/api`) |
| `MONGO_ROOT_PASSWORD` | Strong password for MongoDB admin |
| `MONGODB_URI` | Full MongoDB connection string |
| `JWT_SECRET_KEY` | Generate with `openssl rand -hex 32` |
| `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` | Your LLM provider API key |
| `SMTP_*` | Email credentials for magic-link auth |

---

## Step 6: Set Up SSL Certificates (HTTPS)

### Option A: Let's Encrypt (Recommended)

If you have a domain pointing to your droplet:

```bash
chmod +x scripts/setup-ssl.sh
./scripts/setup-ssl.sh your-domain.com your-email@example.com
```

This will:
- Obtain SSL certificates from Let's Encrypt
- Store them in `nginx/ssl/`
- Create an auto-renewal script at `scripts/renew-ssl.sh`

**Enable auto-renewal:**

```bash
crontab -e
# Add this line:
0 3 * * * /root/epi-meta-extractor/scripts/renew-ssl.sh
```

### Option B: Self-Signed Certificates (Development Only)

If you don't have a domain:

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"
```

---

## Step 7: Deploy the Application

Run the deployment script:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Or manually:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Step 8: Verify Deployment

Check that all services are running:

```bash
docker compose -f docker-compose.prod.yml ps
```

Expected output:

```
NAME                IMAGE                      STATUS
epi-meta-nginx     nginx:alpine               Up (healthy)
epi-meta-frontend  epi-meta-extractor-frontend Up (healthy)
epi-meta-backend   epi-meta-extractor-backend   Up (healthy)
epi-meta-mongodb   mongo:7.0                  Up (healthy)
epi-meta-qdrant    qdrant/qdrant:latest       Up
```

**Test endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `https://your-domain.com` | Frontend (Next.js) |
| `https://your-domain.com/api/health` | Backend health check |
| `https://your-domain.com/api/docs` | FastAPI Swagger UI |

---

## Step 9: Monitoring & Logs

**View logs:**

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx
```

**Monitor resource usage:**

```bash
docker stats
```

---

## Maintenance

### Update the Application

```bash
cd epi-meta-extractor
git pull origin main
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

### Backup MongoDB Data

```bash
docker compose -f docker-compose.prod.yml exec mongodb mongodump \
  --username admin --password YOUR_PASSWORD \
  --db epi_meta_extractor --out /data/backup
```

### Backup Qdrant Data

Qdrant data is stored in the `qdrant_data` Docker volume. Back up the volume:

```bash
docker run --rm -v epi-meta-extractor_qdrant_data:/source \
  -v $(pwd)/backups:/backup alpine \
  tar czf /backup/qdrant-backup.tar.gz -C /source .
```

---

## Troubleshooting

### Services won't start

```bash
# Check for port conflicts
sudo lsof -i :80
sudo lsof -i :443
sudo lsof -i :8000
sudo lsof -i :3000

# View detailed logs
docker compose -f docker-compose.prod.yml logs --tail=100
```

### SSL certificate issues

```bash
# Verify certificates exist
ls -la nginx/ssl/

# Check nginx config syntax
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

### MongoDB connection errors

```bash
# Check MongoDB is running
docker compose -f docker-compose.prod.yml exec mongodb mongosh \
  --username admin --password YOUR_PASSWORD \
  --eval "db.adminCommand('ping')"
```

### Out of memory

If your droplet has limited RAM, reduce Gunicorn workers in `Dockerfile.prod`:

```dockerfile
CMD ["gunicorn", "backend.app:app", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "2", ...]
```

---

## Architecture Overview

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│  Frontend   │ (Next.js :3000)
│  (:80/443)  │     │  (Next.js)  │
└──────┬──────┘     └─────────────┘
       │
       │ /api/*
       ▼
┌─────────────┐     ┌─────────────┐
│   Backend   │────▶│   MongoDB   │ (:27017)
│  (FastAPI)  │     │   (Data)    │
│   (:8000)   │     └─────────────┘
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Qdrant    │ (:6333)
│ (Vectors)   │
└─────────────┘
```

---

## Security Checklist

- [ ] Changed all default passwords in `.env`
- [ ] Generated a strong `JWT_SECRET_KEY`
- [ ] Set `COOKIE_SECURE=true` (requires HTTPS)
- [ ] Configured SMTP with app-specific password (not main password)
- [ ] Restricted MongoDB port (not exposed publicly)
- [ ] Enabled firewall (UFW) — only allow 22, 80, 443
- [ ] Set up SSL/TLS certificates
- [ ] Enabled automatic security updates

---

## Support

For issues or questions, please open a GitHub issue at:
https://github.com/Blaise-bf/epi-meta-extractor/issues
