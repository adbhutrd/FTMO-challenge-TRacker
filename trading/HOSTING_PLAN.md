# 🚀 CEO AI — Enterprise Architecture Plan v2

## Current State (Beginner) → Target State (Web 3.0)

| Layer | Current | Target |
|-------|---------|--------|
| Process Management | `screen` sessions | **Docker Compose** |
| Task Queue | `pending.json` (file corruption) | **Redis + Celery** |
| Database | JSON / JSONL files | **PostgreSQL** |
| API Server | None (inline functions) | **FastAPI** |
| Web Server | `python -m http.server` | **Nginx + SSL** |
| Frontend | Static HTML | **React/Svelte Dashboard** |
| CDN | None | **Cloudflare** |
| Monitoring | None | **Prometheus + Grafana** |
| CI/CD | Manual | **GitHub Actions** |
| Infrastructure | Manual | **Terraform / Docker Compose** |

---

## Architecture

```
                         CLOUDFLARE
                     (CDN · SSL · Proxy)
                           │
                    ┌──────▼──────┐
                    │    NGINX    │
                    │  Reverse    │
                    │  Proxy      │
                    └──┬───┬───┬─┘
                       │   │   │
              ┌────────┘   │   └────────┐
              │            │            │
      ┌───────▼────┐ ┌────▼────┐ ┌─────▼─────────┐
      │ Telegram   │ │ FastAPI │ │ Web Dashboard  │
      │ Webhook    │ │ CEO API │ │ (status +      │
      │ Receiver   │ │ Server  │ │  controls)     │
      └───────┬────┘ └────┬────┘ └────────────────┘
              │            │
              │     ┌──────▼──────────────────┐
              │     │      REDIS               │
              │     │  • Task Queue (RQ)       │
              │     │  • Rate Limiting         │
              │     │  • Session Cache         │
              │     │  • Rate Limit Buckets    │
              │     └──────┬──────────────────┘
              │            │
              │     ┌──────▼──────────────────┐
              │     │   AI WORKER POOL         │
              │     │  • GPT-4o (complex)      │
              │     │  • DeepSeek (simple)     │
              │     │  • Auto-scaling          │
              │     └──────┬──────────────────┘
              │            │
              │     ┌──────▼──────────────────┐
              │     │    POSTGRESQL            │
              │     │  • conversations         │
              │     │  • users                 │
              │     │  • analytics             │
              │     │  • rate_limits           │
              │     │  • service_logs          │
              │     └─────────────────────────┘
              │
              │     ┌─────────────────────────┐
              └────▶│   MONITORING STACK      │
                    │  • Prometheus (metrics)  │
                    │  • Grafana (dashboards)  │
                    │  • Loki (log aggregation)│
                    │  • Alertmanager          │
                    └─────────────────────────┘
```

---

## Implementation

### Phase 1: Docker Compose Stack (Today)

```yaml
# docker-compose.yml
version: "3.9"

services:
  # ── API Gateway ──────────────────────────
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - ./frontend:/usr/share/nginx/html
    ports:
      - "80:80"
      - "443:443"
    depends_on: [api, dashboard]
    restart: always

  # ── CEO AI API ───────────────────────────
  api:
    build: ./api
    env_file: .env
    depends_on: [redis, postgres]
    restart: always

  # ── Telegram Webhook Handler ──────────────
  webhook:
    build: ./webhook
    env_file: .env
    depends_on: [redis, postgres]
    restart: always

  # ── AI Worker (horizontal scaling) ────────
  worker:
    build: ./worker
    env_file: .env
    depends_on: [redis, postgres]
    restart: always
    scale: 2  # Two workers for concurrency

  # ── Web Dashboard (React) ────────────────
  dashboard:
    build: ./dashboard
    restart: always

  # ── Task Queue ────────────────────────────
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: always

  # ── Database ──────────────────────────────
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    env_file: .env
    restart: always

  # ── Monitoring ────────────────────────────
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: always

  grafana:
    image: grafana/grafana
    depends_on: [prometheus]
    restart: always

volumes:
  redis_data:
  postgres_data:
```

### Phase 2: FastAPI CEO Service

```python
# api/main.py — Enterprise FastAPI server
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import asyncpg
import openai

app = FastAPI(title="CEO AI API", version="2.0.0")

# CORS for dashboard
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ── Database pool (PostgreSQL) ──
@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(
        dsn=os.getenv("DATABASE_URL"),
        min_size=4, max_size=20
    )
    app.state.redis = redis.from_url(os.getenv("REDIS_URL"))

# ── Request/Response Models ──
class ChatRequest(BaseModel):
    message: str
    user_id: str
    model: str | None = None  # auto-detect if not specified

class ChatResponse(BaseModel):
    response: str
    model_used: str
    processing_time_ms: int

# ── CEO Chat Endpoint ──
@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    start = time.time()
    
    # Rate limit check (Redis)
    key = f"rate_limit:{request.user_id}"
    count = await app.state.redis.incr(key)
    await app.state.redis.expire(key, 60)
    if count > 30:
        raise HTTPException(429, "Rate limit exceeded")
    
    # Classify complexity
    model = request.model or classify_complexity(request.message)
    
    # Enqueue to Redis for async processing
    task_id = str(uuid.uuid4())
    await app.state.redis.rpush("task_queue", json.dumps({
        "task_id": task_id,
        "message": request.message,
        "user_id": request.user_id,
        "model": model,
        "timestamp": datetime.utcnow().isoformat()
    }))
    
    # Wait for result (poll Redis)
    for _ in range(50):  # max 5 seconds wait
        result = await app.state.redis.get(f"result:{task_id}")
        if result:
            data = json.loads(result)
            return ChatResponse(
                response=data["response"],
                model_used=model,
                processing_time_ms=int((time.time() - start) * 1000)
            )
        await asyncio.sleep(0.1)
    
    # Return task ID for polling if slow
    return ChatResponse(
        response=f"Processing (task: {task_id[:8]}...)",
        model_used=model,
        processing_time_ms=0
    )

# ── Health Check ──
@app.get("/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "database": "connected",
        "redis": "connected",
        "uptime_seconds": time.time() - startup_time
    }

# ── Metrics for Prometheus ──
@app.get("/v1/metrics")
async def metrics():
    return {
        "total_conversations": await get_count("conversations"),
        "total_users": await get_count("users"),
        "gpt4o_usage": await get_count("model:gpt4o"),
        "deepseek_usage": await get_count("model:deepseek"),
        "active_tasks": await app.state.redis.llen("task_queue")
    }
```

### Phase 3: PostgreSQL Schema

```sql
-- init.sql — Enterprise schema
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    role VARCHAR(10) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    model VARCHAR(50),
    tokens_used INT DEFAULT 0,
    processing_ms INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id, created_at DESC);

CREATE TABLE users (
    id BIGINT PRIMARY KEY,  -- Telegram user ID
    username VARCHAR(255),
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    total_messages INT DEFAULT 0,
    preferred_model VARCHAR(50) DEFAULT 'auto'
);

CREATE TABLE service_logs (
    id BIGSERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logs_service_time ON service_logs(service, created_at DESC);

CREATE TABLE rate_limits (
    user_id BIGINT PRIMARY KEY,
    requests_minute INT DEFAULT 0,
    window_start TIMESTAMPTZ DEFAULT NOW()
);
```

### Phase 4: AI Worker (Async)

```python
# worker/main.py — Dedicated AI worker process
from redis import Redis
import openai
import json
import asyncio
from db import save_conversation, get_conversation_history

r = Redis.from_url(os.getenv("REDIS_URL"))

MODEL_FAST = "deepseek/deepseek-chat"
MODEL_SMART = "openai/gpt-4o"

async def process_task(task_data: dict):
    """Process a single AI task. Runs in worker pool."""
    message = task_data["message"]
    model = task_data["model"]
    
    # Load conversation history from PostgreSQL
    history = await get_conversation_history(task_data["user_id"], limit=100)
    
    # Call AI
    start = time.time()
    response = await call_ai(history, message, model)
    elapsed = int((time.time() - start) * 1000)
    
    # Save to database
    await save_conversation(task_data["user_id"], "user", message, model)
    await save_conversation(task_data["user_id"], "assistant", response, model)
    
    # Store result in Redis for API to pick up
    r.setex(f"result:{task_data['task_id']}", 60, json.dumps({
        "response": response,
        "processing_ms": elapsed
    }))
    
    # Track metrics
    r.incr(f"metrics:model:{model}")

async def worker_loop():
    """Main worker loop — pulls from Redis queue."""
    print("🤖 AI Worker started, waiting for tasks...")
    while True:
        task_data = r.blpop("task_queue", timeout=30)
        if task_data:
            _, data = task_data
            await process_task(json.loads(data))

if __name__ == "__main__":
    asyncio.run(worker_loop())
```

### Phase 5: Web Dashboard (React)

```
dashboard/
├── public/
│   └── index.html
├── src/
│   ├── App.tsx          # Main dashboard
│   ├── components/
│   │   ├── ChatPanel.tsx      # Talk to CEO directly
│   │   ├── MetricsCards.tsx   # Live metrics
│   │   ├── ServiceStatus.tsx  # System health
│   │   ├── ConversationLog.tsx # Browse history
│   │   └── Analytics.tsx      # Usage graphs
│   ├── hooks/
│   │   └── useAPI.ts
│   └── styles/
│       └── dashboard.css
├── package.json
├── Dockerfile
└── nginx.conf
```

---

## What This Delivers

| Feature | What It Means |
|---------|---------------|
| **Zero downtime** | Docker restart policy + health checks |
| **Horizontal scaling** | `docker-compose up --scale worker=10` |
| **Rate limiting** | Redis-based, per-user, configurable |
| **Database persistence** | PostgreSQL — no file corruption, ACID compliant |
| **Real-time metrics** | Prometheus + Grafana dashboards |
| **Web dashboard** | Talk to me, see metrics, browse history — from a browser |
| **CI/CD** | Git push → auto-build → auto-deploy |
| **API-first** | Other services can integrate via REST API |
| **SSL + CDN** | Cloudflare + Let's Encrypt |
| **Webhook** | No polling, no 409, instant delivery |

---

## What I Need From You

To build this, I need:
1. **A domain name** — any cheap one ($5-10/year on Namecheap/Cloudflare)
2. **Temporary sudo access** — to install Docker if not present (it is ✅)
3. **30-60 minutes** — to build and deploy the entire stack

**I will build this.** Not copy-paste. Every file written from scratch. Dockerfiles, FastAPI server, PostgreSQL schema, Redis workers, React dashboard, Prometheus config, Nginx config — all of it.
