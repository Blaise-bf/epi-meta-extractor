# Deploying Epi Meta Extractor to Railway (Free Tier)

This guide walks you through deploying the **Epi Meta Extractor** to [Railway](https://railway.app) using their free trial credits and external managed services.

---

## Architecture on Railway

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway Platform                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Docker Service (FastAPI)                  │  │
│  │              epi-meta-backend                            │  │
│  │              ~$5/mo equivalent (free trial)              │  │
│  └────────────────────────┬────────────────────────────────┘  │
└───────────────────────────┼───────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ MongoDB Atlas│    │ Qdrant Cloud │    │   DeepSeek   │
│   M0 (Free)  │    │  Free Tier   │    │   / OpenAI   │
└──────────────┘    └──────────────┘    └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Frontend: Vercel (Recommended) or Railway Static            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Next.js Static / Standalone                          │ │
│  │  FREE on Vercel                                       │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

> **Note:** Railway's free tier is credit-based ($5 equivalent). Running a single small service 24/7 will consume this quickly. For the frontend, we strongly recommend **Vercel** (always free for Next.js).

---

## Prerequisites

- [Railway](https://railway.app) account
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) account
- [Qdrant Cloud](https://cloud.qdrant.io/) account (optional)
- [Vercel](https://vercel.com) account (for frontend — free)
- LLM API key (DeepSeek or OpenAI)

---

## Step 1: Set Up External Services

### MongoDB Atlas (Free M0)

Follow the same steps as in [DEPLOY_RENDER.md](./DEPLOY_RENDER.md#step-1-set-up-mongodb-atlas-free-m0-cluster).

Copy your connection string:
```
mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/epi_meta_extractor?retryWrites=true&w=majority
```

### Qdrant Cloud (Optional)

Follow the same steps as in [DEPLOY_RENDER.md](./DEPLOY_RENDER.md#step-2-set-up-qdrant-cloud-free-tier).

---

## Step 2: Deploy Backend to Railway

### Option A: Deploy from GitHub Repo (Recommended)

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `Blaise-bf/epi-meta-extractor`
4. Railway will detect the `railway.json` and `Dockerfile.prod`
5. Click **Deploy**

### Option B: Deploy via CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# Deploy
railway up
```

---

## Step 3: Configure Environment Variables

In the Railway dashboard, go to your service → **Variables** tab:

| Variable | Value | Source |
|----------|-------|--------|
| `MONGODB_URI` | `mongodb+srv://...` | MongoDB Atlas |
| `MONGODB_DB_NAME` | `epi_meta_extractor` | — |
| `QDRANT_URL` | `https://xxxx.cloud.qdrant.io:6333` | Qdrant Cloud |
| `QDRANT_API_KEY` | `eyJ...` | Qdrant Cloud |
| `LLM_PROVIDER` | `deepseek` | — |
| `DEEPSEEK_API_KEY` | `sk-...` | DeepSeek |
| `DEEPSEEK_MODEL` | `deepseek-chat` | — |
| `DEEPSEEK_API_URL` | `https://api.deepseek.com/v1` | — |
| `OPENAI_API_KEY` | `sk-...` | OpenAI (optional) |
| `PDF_PARSER_PRIMARY` | `marker` | — |
| `PDF_PARSER_FALLBACK_CHAIN` | `marker,pypdf` | — |
| `MARKER_ENABLED` | `true` | — |
| `MARKER_TIMEOUT` | `300` | — |
| `GROBID_ENABLED` | `false` | — |
| `JWT_SECRET_KEY` | Generate: `openssl rand -hex 32` | You |
| `JWT_ALGORITHM` | `HS256` | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | — |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | — |
| `MAGIC_LINK_EXPIRE_MINUTES` | `15` | — |
| `FRONTEND_ORIGIN` | `https://epi-meta-frontend.vercel.app` | Your frontend URL |
| `COOKIE_SECURE` | `true` | — |
| `SMTP_HOST` | `smtp.gmail.com` | Your provider |
| `SMTP_PORT` | `587` | — |
| `SMTP_USERNAME` | `your-email@gmail.com` | — |
| `SMTP_PASSWORD` | `app-password` | — |
| `SMTP_FROM` | `noreply@your-domain.com` | — |
| `SMTP_TLS` | `true` | — |
| `DEBUG` | `false` | — |
| `UPLOAD_DIR` | `/tmp/raw_pdfs` | — |
| `TEMP_DIR` | `/tmp` | — |

> **Important:** Railway automatically provides a `PORT` environment variable. The `railway.json` uses `$PORT` for Gunicorn binding.

---

## Step 4: Deploy Frontend to Vercel

Railway's free credits are best spent on the backend. For the Next.js frontend, **Vercel is free and optimized for Next.js**.

### 4a. Prepare the Frontend

Ensure `frontend/next.config.ts` has the correct API URL setup. We'll use Vercel's environment variables:

```typescript
// frontend/next.config.ts
const nextConfig = {
  output: "standalone",  // or "export" for static
  // ... rest of config
};
```

### 4b. Deploy to Vercel

1. Go to [Vercel](https://vercel.com) → **Add New Project**
2. Import `Blaise-bf/epi-meta-extractor`
3. **Framework Preset**: Next.js
4. **Root Directory**: `frontend`
5. **Build Command**: `next build`
6. **Output Directory**: (leave default for standalone, or `.next`)
7. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://epi-meta-backend-production.up.railway.app`
8. Click **Deploy**

### 4c. Update CORS

After Vercel deploys, copy the frontend URL and update Railway:

```bash
railway variables --set FRONTEND_ORIGIN=https://epi-meta-frontend.vercel.app
```

---

## Step 5: Verify Deployment

| Service | URL | Check |
|---------|-----|-------|
| Backend | `https://...up.railway.app/health` | `{"status":"healthy"}` |
| Backend | `https://...up.railway.app/api/docs` | Swagger UI |
| Frontend | `https://...vercel.app` | App loads |

---

## Railway-Specific Tips

### Using Volumes (Not Available on Free Tier)

Railway volumes are paid. On the free tier:
- Uploaded PDFs are stored in **ephemeral disk** (`/tmp`) and lost on redeploy
- For persistent storage, integrate **AWS S3**, **Cloudflare R2**, or **Supabase Storage**

### Custom Domain

1. In Railway dashboard → **Settings** → **Domains**
2. Add your domain and follow DNS instructions
3. In Vercel → **Project Settings** → **Domains** → add the same domain

### Monitoring

Railway provides built-in metrics:
- CPU / Memory usage
- Request logs
- Deployment history

Go to **Deployments** tab → click a deployment → **Logs** / **Metrics**

---

## Free Tier Limitations

| Limitation | Details |
|------------|---------|
| **$5 credit** | Enough for ~1 small service running 24/7 for a month |
| **No persistent volumes** | Data lost on restart unless using external DB |
| **Shared CPU** | Performance varies based on platform load |
| **Sleeping** | Services may sleep on very low usage (less aggressive than Render) |

### Cost Optimization

- **Backend on Railway** (~$5/mo equivalent) — use free trial credits
- **Frontend on Vercel** ($0) — always free for hobby projects
- **MongoDB Atlas M0** ($0) — free forever
- **Qdrant Cloud Free** ($0) — 1 GB storage
- **Total fixed cost after credits**: **$0** (or ~$5/mo if paying for Railway)

---

## Troubleshooting

### "Service crashed on startup"

Check logs in Railway dashboard → **Deployments** → **Logs**.

Common causes:
- Missing `MONGODB_URI`
- `PORT` not bound correctly (must use `$PORT`, not hardcoded `8000`)
- Docker build failure (check **Build Logs**)

### "CORS errors"

- Verify `FRONTEND_ORIGIN` matches your Vercel domain exactly
- Include `https://` and no trailing slash

### "Build takes too long"

- Railway builds from scratch each deploy
- Consider using a smaller base image (`python:3.13-slim`) if `marker-pdf` allows it
- Add `.dockerignore` to reduce build context (already included)

---

## CLI Cheat Sheet

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# View logs
railway logs

# Set variables
railway variables --set KEY=value

# Deploy
railway up

# Open dashboard
railway open
```

---

## Next Steps

- Add a custom domain for a professional look
- Set up Cloudflare for CDN and DDoS protection
- Configure S3/R2 for persistent file uploads
- Add Railway's **cron jobs** for scheduled tasks (paid feature)
