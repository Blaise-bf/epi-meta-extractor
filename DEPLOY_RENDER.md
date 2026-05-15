# Deploying Epi Meta Extractor to Render (Free Tier)

This guide walks you through deploying the **Epi Meta Extractor** to [Render](https://render.com) using their free tier and external managed services for the database layer.

---

## Architecture on Render

```
┌─────────────────────────────────────────────────────────────┐
│                         Render Platform                      │
│  ┌─────────────────┐        ┌──────────────────────────┐   │
│  │  Static Site    │        │   Web Service (Docker)   │   │
│  │  (Next.js)      │───────▶│   FastAPI Backend        │   │
│  │  epi-meta-frontend      │   epi-meta-backend       │   │
│  │  FREE — always on       │   FREE — sleeps 15min    │   │
│  └─────────────────┘        └───────────┬──────────────┘   │
│                                         │                  │
└─────────────────────────────────────────┼──────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │ MongoDB Atlas│    │ Qdrant Cloud │    │   DeepSeek   │
            │   M0 (Free)  │    │  Free Tier   │    │   / OpenAI   │
            └──────────────┘    └──────────────┘    └──────────────┘
```

---

## Prerequisites

- [Render](https://render.com) account (free tier works)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) account
- [Qdrant Cloud](https://cloud.qdrant.io/) account (optional — skip if not using RAG/vectors)
- LLM API key (DeepSeek or OpenAI)

---

## Step 1: Set Up MongoDB Atlas (Free M0 Cluster)

1. Go to [MongoDB Atlas](https://cloud.mongodb.com) → Create New Project
2. **Build a Database** → Choose **M0 (Free)** tier
3. Select a cloud provider region close to Render's region (US East / Oregon)
4. Create a database user with a strong password
5. In **Network Access**, add `0.0.0.0/0` (allow from anywhere — required for Render)
6. Go to **Database** → **Connect** → **Drivers** → **Python**
7. Copy the connection string:
   ```
   mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/epi_meta_extractor?retryWrites=true&w=majority
   ```

---

## Step 2: Set Up Qdrant Cloud (Free Tier)

1. Go to [Qdrant Cloud](https://cloud.qdrant.io/) → Sign Up
2. Create a **Free** cluster (1 node, 1 GB RAM, 4 GB disk)
3. Once created, go to **Access** → copy the **Cluster URL** and **API Key**

> **Skip this step** if you don't need vector search / RAG features. Set `USE_RAG_CHAINS=false` later.

---

## Step 3: Deploy via Render Blueprint (Recommended)

Render supports **Infrastructure as Code** via `render.yaml`.

### 3a. Fork or push this repo to GitHub

Ensure your repo contains the `render.yaml` file at the root.

### 3b. Create Blueprint in Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Blueprint**
3. Connect your GitHub repo: `Blaise-bf/epi-meta-extractor`
4. Render will read `render.yaml` and show you the services to create
5. Click **Apply**

### 3c. Configure Environment Variables

After the blueprint creates the services, you **must** set the secret variables manually:

**For `epi-meta-backend`:**

| Variable | Value | Source |
|----------|-------|--------|
| `MONGODB_URI` | `mongodb+srv://...` | MongoDB Atlas |
| `QDRANT_URL` | `https://xxxx.cloud.qdrant.io:6333` | Qdrant Cloud |
| `QDRANT_API_KEY` | `eyJ...` | Qdrant Cloud |
| `DEEPSEEK_API_KEY` | `sk-...` | DeepSeek Platform |
| `OPENAI_API_KEY` | `sk-...` | OpenAI (optional) |
| `JWT_SECRET_KEY` | Auto-generated | Render generated this |
| `FRONTEND_ORIGIN` | `https://epi-meta-frontend-xxx.onrender.com` | Your frontend URL |
| `SMTP_HOST` | `smtp.gmail.com` | Your email provider |
| `SMTP_USERNAME` | `your-email@gmail.com` | Your email |
| `SMTP_PASSWORD` | `xxxx xxxx xxxx xxxx` | App-specific password |
| `SMTP_FROM` | `noreply@your-domain.com` | Sender address |

**For `epi-meta-frontend`:**

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://epi-meta-backend-xxx.onrender.com` |

> **Note:** `NEXT_PUBLIC_API_URL` must be set **before** the frontend builds, because Next.js bakes public env vars into the bundle at build time.

---

## Step 4: Manual Deploy (Alternative to Blueprint)

If you prefer not to use the blueprint:

### Backend (Web Service)

1. **New** → **Web Service**
2. Connect your GitHub repo
3. **Runtime**: Docker
4. **Dockerfile Path**: `./Dockerfile.prod`
5. **Plan**: Free
6. Set all environment variables from Step 3c
7. **Create Web Service**

### Frontend (Static Site)

1. **New** → **Static Site**
2. Connect the same repo
3. **Build Command**: `cd frontend && npm install && npm run build`
4. **Publish Directory**: `frontend/dist`
5. Set `NEXT_PUBLIC_API_URL` to your backend URL
6. **Create Static Site**

---

## Step 5: Verify Deployment

| Endpoint | Expected Result |
|----------|---------------|
| `https://epi-meta-backend-xxx.onrender.com/health` | `{"status":"healthy"}` |
| `https://epi-meta-backend-xxx.onrender.com/api/docs` | FastAPI Swagger UI |
| `https://epi-meta-frontend-xxx.onrender.com` | Next.js app loads |

---

## Important: Free Tier Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **Backend sleeps after 15 min idle** | First request after inactivity takes ~30-60s (cold start) | Use a cron job (e.g., UptimeRobot) to ping `/health` every 10 min |
| **No persistent disk** | Uploaded PDFs are lost on redeploy | Use cloud storage (S3, Cloudinary) or accept ephemeral uploads |
| **512 MB RAM (backend)** | Large PDFs may fail | Process smaller PDFs; upgrade to Starter ($7/mo) for 512 MB → 1 GB |
| **100 GB egress/month** | Fine for low traffic | Monitor in Render dashboard |

### Keeping the Backend Awake (Optional)

Use a free uptime monitor to prevent cold starts:

1. [UptimeRobot](https://uptimerobot.com/) — Free plan: 50 monitors, 5-min intervals
2. Set monitor URL: `https://epi-meta-backend-xxx.onrender.com/health`
3. Set interval: 5 minutes

This keeps your backend alive without exceeding Render's free limits.

---

## Updating the App

Render auto-deploys on every push to `main` (if `autoDeploy: true` in `render.yaml`).

To deploy manually:
1. Go to the service in Render dashboard
2. Click **Manual Deploy** → **Deploy Latest Commit**

---

## Troubleshooting

### "Build failed" on frontend

- Ensure `NEXT_PUBLIC_API_URL` is set **before** the build
- Check that `frontend/dist` is created by `npm run build`
- Verify `next.config.ts` has `output: 'export'` or `output: 'standalone'`

### "Cannot connect to MongoDB"

- Verify `MONGODB_URI` uses `mongodb+srv://` (not `mongodb://`)
- Check Atlas Network Access allows `0.0.0.0/0`
- Ensure the database user password doesn't contain special characters that need URL-encoding

### "Backend cold start too slow"

- The free tier spins down after 15 min. Use UptimeRobot or upgrade to Starter.
- Reduce Docker image size: use `python:3.13-slim` in Dockerfile (may require testing)

### "CORS errors in browser"

- Ensure `FRONTEND_ORIGIN` exactly matches your frontend URL (including `https://`)
- Check for trailing slashes — `https://example.com` ≠ `https://example.com/`

---

## Cost Estimate (Free Tier)

| Service | Cost |
|---------|------|
| Render Web Service (backend) | **$0** |
| Render Static Site (frontend) | **$0** |
| MongoDB Atlas M0 | **$0** |
| Qdrant Cloud Free | **$0** |
| DeepSeek API | Pay-per-use (~$0.001 per 1K tokens) |
| **Total fixed cost** | **$0/month** |

If you need the backend always-on, upgrade to Render's **Starter** plan ($7/month).

---

## Next Steps

- Set up a custom domain in Render (free on all plans)
- Configure Cloudflare in front of Render for CDN + DDoS protection
- Add S3/R2 for persistent PDF storage if needed
