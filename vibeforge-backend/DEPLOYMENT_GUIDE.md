# VibeForge Backend Deployment Guide

Complete guide for deploying the unified LLM service to production.

## 🚀 Quick Start

### 1. Local Development

```bash
# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]
pip install -e .[llm]

# Configure providers
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run server
uvicorn app.main:app --reload --port 8000
```

### 2. Testing

```bash
# Run test suite
python3 test_llm_service.py

# Run integration examples
python3 llm_service_examples.py

# Run specific endpoint
curl -X POST http://localhost:8000/v1/vibeforge/run \
  -H "Content-Type: application/json" \
  -d '{"workspace_id":"test","model":"gpt-4","prompt":"Hello"}'
```

## 📋 Environment Setup

### Required Environment Variables

```bash
# OpenAI API (required for GPT models)
export OPENAI_API_KEY="sk-..."

# Anthropic API (required for Claude models)
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama (optional, defaults to localhost:11434)
export OLLAMA_BASE_URL="http://localhost:11434"
```

### Create .env File

```bash
# Create file at project root
cat > .env << 'EOF'
# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Logging
LOG_LEVEL=INFO
EOF
```

### Load Environment Variables

```bash
# Bash/Zsh
source .env

# Or use python-dotenv in code
from dotenv import load_dotenv
load_dotenv()
```

## 🐳 Docker Deployment

### Build Docker Image

```bash
# Build image
docker build -t vibeforge-backend:latest .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="sk-..." \
  -e ANTHROPIC_API_KEY="sk-ant-..." \
  -e LOG_LEVEL=INFO \
  vibeforge-backend:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OLLAMA_BASE_URL: http://ollama:11434
      LOG_LEVEL: INFO
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

Run with:

```bash
docker-compose up -d
```

## 🔐 Security Configuration

### API Key Management

**Development**:

- Store in `.env` (git-ignored)
- Load with `python-dotenv`

**Production**:

- Use AWS Secrets Manager
- Use Azure Key Vault
- Use environment variables from CI/CD

### CORS Configuration

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Production domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting

```python
# Add rate limiter
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/v1/vibeforge/run")
@limiter.limit("100/minute")
async def create_run(request: Request, body: CreateRunRequest):
    ...
```

## 📊 Monitoring & Observability

### Logging Configuration

```python
# app/main.py
import logging
import sys

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('vibeforge.log')
    ]
)
```

### Structured Logging

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger("llm_service")

def log_request(model: str, tokens: int, provider: str):
    logger.info(json.dumps({
        "timestamp": datetime.utcnow().isoformat(),
        "event": "llm_request",
        "model": model,
        "tokens": tokens,
        "provider": provider,
    }))
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, CollectorRegistry

# Prometheus metrics
REQUESTS = Counter('llm_requests_total', 'Total LLM requests', ['model', 'provider'])
TOKENS = Counter('llm_tokens_total', 'Total tokens used', ['provider'])
LATENCY = Histogram('llm_latency_ms', 'Request latency in ms', ['provider'])

# Track metrics
REQUESTS.labels(model="gpt-4", provider="openai").inc()
TOKENS.labels(provider="openai").inc(response.total_tokens)
LATENCY.labels(provider="openai").observe(response.latency_ms)
```

## 🧪 Testing Strategy

### Unit Tests

```bash
# Run unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=app --cov-report=html
```

### Integration Tests

```bash
# Run integration tests (requires API keys)
pytest tests/integration/ -v

# Run with specific provider
pytest tests/integration/ -k "test_gpt" -v
```

### Load Testing

```python
# locustfile.py
from locust import HttpUser, task, between

class LLMUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_run(self):
        self.client.post("/v1/vibeforge/run", json={
            "workspace_id": "test",
            "model": "gpt-4",
            "prompt": "Hello world"
        })
```

Run with:

```bash
locust -f locustfile.py --host=http://localhost:8000
```

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: pip install -e .[dev,llm]
      - run: pytest tests/ -v
      - run: python3 test_llm_service.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build and push Docker
        run: |
          docker build -t vibeforge-backend:latest .
          docker tag vibeforge-backend:latest \
            ${{ secrets.REGISTRY }}/vibeforge-backend:${{ github.sha }}
          docker push ${{ secrets.REGISTRY }}/vibeforge-backend:latest
```

## 📈 Performance Optimization

### Token Estimation Cache

```python
from functools import lru_cache

@lru_cache(maxsize=1024)
def estimate_tokens_cached(model: str, text: str) -> int:
    return estimate_tokens(model, text)
```

### Response Caching

```python
from aiocache import cached, TTLMemoryCache

@cached(cache=TTLMemoryCache(), ttl=3600)
async def get_model_info(model: str):
    return await service.get_model_config(model)
```

### Connection Pooling

```python
# Reuse HTTP connections
import httpx

async_client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(max_connections=100)
)
```

## 🆘 Troubleshooting

### API Key Issues

```bash
# Verify API keys are set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Test API key validity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Provider Connection Issues

```python
# Check provider status
from app.services.llm_service import get_llm_service

service = get_llm_service()
status = service.get_provider_status()
print(status)
```

### Timeout Issues

```python
# Increase timeout for slow networks
response = await call_llm(
    model="gpt-4",
    prompt="Your prompt",
    timeout=600  # 10 minutes
)
```

## 📝 Monitoring Checklist

- [ ] Logging configured (file + stdout)
- [ ] Metrics collection active (Prometheus)
- [ ] Health check endpoint verified
- [ ] API key rotation schedule planned
- [ ] Rate limiting configured
- [ ] Error alerting setup
- [ ] Performance baselines established
- [ ] Backup/failover plan in place

## 🚀 Production Deployment Steps

1. **Prepare**

   - [ ] Review security settings
   - [ ] Configure environment variables
   - [ ] Setup database backups
   - [ ] Configure monitoring/alerts

2. **Deploy**

   - [ ] Build Docker image
   - [ ] Push to registry
   - [ ] Deploy to production environment
   - [ ] Verify health checks

3. **Verify**

   - [ ] Test all LLM providers
   - [ ] Check logs for errors
   - [ ] Monitor metrics
   - [ ] Verify API responses

4. **Monitor**
   - [ ] Setup alerts
   - [ ] Track error rates
   - [ ] Monitor token usage
   - [ ] Track latency metrics

## 📞 Support

For deployment issues:

1. Check logs: `tail -f vibeforge.log`
2. Check status: `/health` endpoint
3. Verify configuration: `env | grep OPENAI`
4. Test directly: `python3 test_llm_service.py`

---

**Last Updated**: 2025-11-18
**Status**: ✅ **READY FOR DEPLOYMENT**
