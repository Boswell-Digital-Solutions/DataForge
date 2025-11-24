# AuthorForge

<h1 align="center">AuthorForge</h1>
<h3 align="center">AI-Powered Creative Writing Platform</h3>
<h4 align="center">Genre-aware writing assistance for the Forge Ecosystem</h4>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Alpha-blue" alt="Alpha">
  <img src="https://img.shields.io/badge/License-Commercial-red" alt="Commercial">
  <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-0.104-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/Anthropic-Claude-purple" alt="Anthropic Claude">
</p>

---

> **📄 License (Commercial)**  
> This product is commercial, closed-source software owned by **Boswell Digital Solutions LLC (BDS)**.  
> You may not redistribute, modify, reverse engineer, or use in derivative products.  
> All rights reserved © 2025 Boswell Digital Solutions LLC.  
> Commercial licensing inquiries: charlesboswell@boswelldigitalsolutions.com

---

**AuthorForge** is an **alpha-stage** AI-powered writing platform that provides genre-aware creative assistance with deep integration into the Forge Ecosystem. It combines narrative structuring, character development, pacing analysis, and AI-powered research through unified DataForge knowledge bases and NeuroForge LLM orchestration.

Built specifically for creative writers, AuthorForge understands the unique requirements of Fantasy, Sci-Fi, Christian Fiction, and general creative writing, providing specialized guidance, worldbuilding tools, and genre-appropriate AI responses.

## 📘 Table of Contents

1. [Overview](#-overview)
2. [Key Features](#-key-features)
3. [Supported Genres](#-supported-genres)
4. [Quick Start](#-quick-start)
5. [API Endpoints](#-api-endpoints)
6. [Genre System](#-genre-system)
7. [DataForge Integration](#-dataforge-integration)
8. [Project Structure](#-project-structure)
9. [Development](#-development)
10. [Troubleshooting](#-troubleshooting)
11. [Deployment](#-deployment)
12. [License](#-license)

---

## 📖 Overview

AuthorForge is a **cathedral-level creative writing platform** that provides genre-specific AI assistance for professional authors. It integrates deeply with the Forge Ecosystem to deliver intelligent writing support:

### Ecosystem Integration

| Component      | Role                                                                             | Status      |
| -------------- | -------------------------------------------------------------------------------- | ----------- |
| **DataForge**  | Unified knowledge base for writing craft, narrative structure, genre conventions | ✅ Required |
| **NeuroForge** | AI orchestration with genre-specific model routing and domain adapters           | 🔄 Optional |
| **VibeForge**  | Entry product that recommends AuthorForge for creative projects                  | 🔗 Related  |

### What Makes AuthorForge Special

- **Genre Intelligence**: Understands the unique requirements of Fantasy, Sci-Fi, Christian Fiction, and general creative writing
- **Context-Aware Research**: Searches your personal writing craft library with genre-specific prompts
- **Narrative Tools**: Character arcs, plot development, pacing analysis, worldbuilding support
- **AI Smithy**: Brainstorming engine with genre templates and expansion capabilities
- **Semantic Knowledge Base**: Powered by DataForge's vector embeddings for intelligent content retrieval

---

## ✨ Key Features

### 📚 Multi-Genre Support

- Fantasy, Sci-Fi, Christian Fiction, and General writing frameworks
- Genre-specific knowledge domains
- Tailored AI system prompts
- Specialized brainstorming templates

### 🔍 AI Research Assistant

- Genre-aware synthesis from your personal knowledge base
- Semantic search across writing craft documents
- Source attribution and similarity scores
- Context-aware responses

### 📖 Narrative Structuring

- Character arc development
- Plot structuring and pacing
- Theme exploration
- Worldbuilding assistance

### 💡 Smithy Brainstorming

- AI-powered story ideation
- Concept expansion (character, plot, worldbuilding, themes)
- Genre-specific hooks and prompts
- Technology/magic/spiritual system design

### 🔗 DataForge Integration

- Semantic search across writing craft library
- Domain-based content organization
- Vector similarity matching
- Automatic source citation

### 🎯 NeuroForge Orchestration (Optional)

- Champion model selection for creative content
- Adaptive routing based on query type
- Performance optimization
- Cost-effective model usage

## 🎭 Supported Genres

AuthorForge provides specialized assistance across four major creative writing genres, each with dedicated knowledge domains and AI prompts.

### 🧙 Fantasy

**Knowledge Domains:**

- `fantasy_craft` - Fantasy writing techniques
- `worldbuilding` - World systems and mythology
- `writing_craft` - General narrative structure

**Specialized Features:**

- Magic system design and limitations
- Worldbuilding and mythology creation
- Epic storytelling patterns
- Fantasy-specific narrative conventions
- Hero's journey and quest structures

**Sample Research Questions:**

```
"How do I create a unique magic system with clear rules?"
"What are the key elements of effective worldbuilding?"
"How do I pace an epic fantasy novel?"
```

### 🚀 Sci-Fi

**Knowledge Domains:**

- `scifi_craft` - Science fiction writing techniques
- `worldbuilding` - Future societies and tech systems
- `writing_craft` - General narrative structure

**Specialized Features:**

- Technology and science concept development
- Future society worldbuilding
- Space opera and hard sci-fi conventions
- Scientific accuracy and plausibility
- Speculative extrapolation techniques

**Sample Research Questions:**

```
"How do I make my future technology feel believable?"
"What are the differences between hard and soft sci-fi?"
"How do I create a unique alien species?"
```

### ✝️ Christian Fiction

**Knowledge Domains:**

- `christian_fiction_craft` - Christian fiction techniques
- `biblical_themes` - Scripture and theology references
- `writing_craft` - General narrative structure

**Specialized Features:**

- Biblical themes and parallels
- Spiritual journey and character arcs
- Faith integration in narrative
- Scripture connections and applications
- Redemptive storytelling patterns

**Sample Research Questions:**

```
"How do I weave biblical themes naturally into my story?"
"What are effective ways to show character spiritual growth?"
"How do I write faith authentically without being preachy?"
```

### 📝 General

**Knowledge Domains:**

- `writing_craft` - Universal writing techniques

**Specialized Features:**

- Character development and arcs
- Plot structure and pacing
- Dialogue and narrative voice
- Theme exploration
- Revision and editing strategies

**Sample Research Questions:**

```
"How do I write compelling dialogue?"
"What are the key elements of character development?"
"How do I improve my narrative pacing?"
```

## Quick Start

### Prerequisites

- Python 3.11+
- DataForge running on port 8001 ([see DataForge README](../DataForge/README.md))
- Anthropic API key

### 1. Setup Python Environment

```bash
cd AuthorForge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Required:
# - ANTHROPIC_API_KEY (get from https://console.anthropic.com/)
# - DATAFORGE_URL (default: http://localhost:8001)
```

### 3. Ensure DataForge is Running

```bash
# In a separate terminal
cd ../DataForge
uvicorn app.main:app --port 8001

# Verify it's running
curl http://localhost:8001/health
```

### 4. Run AuthorForge

```bash
# Development mode
uvicorn app.main:app --reload --port 8000

# Or run directly
python -m app.main
```

The API will be available at `http://localhost:8000`

### 5. Explore the API

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Research Assistant

**POST /research/query** - Ask writing craft questions

```bash
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I create a unique magic system?",
    "genre": "fantasy",
    "max_results": 5
  }'
```

**Response:**

```json
{
  "query": "How do I create a unique magic system?",
  "genre": "fantasy",
  "answer": "According to Source 1, a unique magic system...",
  "sources": [
    {
      "content": "...",
      "document_title": "Magic System Design",
      "similarity_score": 0.92
    }
  ]
}
```

### Smithy Brainstorming

**POST /smithy/brainstorm** - Generate story ideas

```bash
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A colony ship discovers an ancient alien artifact",
    "genre": "scifi",
    "num_ideas": 5
  }'
```

**Response:**

```json
{
  "prompt": "A colony ship discovers...",
  "genre": "scifi",
  "ideas": [
    {
      "title": "The Sleeper Signal",
      "description": "When the colony ship Aurora...",
      "themes": ["first contact", "humanity's future", "sacrifice"],
      "technology": "Quantum entanglement artifact",
      "worldbuilding_notes": "...",
      "character_hooks": ["reluctant captain", "alien sympathizer"]
    }
  ]
}
```

**POST /smithy/expand** - Expand a story idea

```bash
curl -X POST http://localhost:8000/smithy/expand \
  -H "Content-Type: application/json" \
  -d '{
    "idea_title": "The Sleeper Signal",
    "idea_description": "When the colony ship Aurora...",
    "genre": "scifi",
    "aspect": "character"
  }'
```

Aspect options: `character`, `plot`, `worldbuilding`, `themes`
Genre-specific: `magic` (fantasy), `technology` (scifi), `spiritual` (christian_fiction)

## Genre System

AuthorForge uses genre-aware prompts to tailor AI responses:

```python
# Example: Research query with genre
{
  "query": "How do I write compelling dialogue?",
  "genre": "fantasy",  # or "scifi", "christian_fiction", "general"
  "max_results": 5
}
```

Each genre has:

- Specific knowledge base domains in DataForge
- Custom AI system prompts
- Genre-appropriate response formatting
- Specialized brainstorming templates

## DataForge Integration

AuthorForge queries DataForge domains based on genre:

| Genre             | DataForge Domains                                       |
| ----------------- | ------------------------------------------------------- |
| Fantasy           | fantasy_craft, worldbuilding, writing_craft             |
| Sci-Fi            | scifi_craft, worldbuilding, writing_craft               |
| Christian Fiction | christian_fiction_craft, biblical_themes, writing_craft |
| General           | writing_craft                                           |

### Setting Up Domains

See [DataForge Domain Setup](../DataForge/README.md#domains) for creating domains.

## Project Structure

```
AuthorForge/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── genres.py        # Genre system
│   └── api/
│       ├── __init__.py
│       ├── research.py      # Research endpoints
│       └── smithy.py        # Brainstorming endpoints
├── requirements.txt
├── .env.example
└── README.md
```

## Development

### Adding a New Genre

1. Add genre to `Genre` enum in `app/models/genres.py`
2. Create `GenreConfig` with domain mappings and prompts
3. Add to `GENRE_CONFIGS` dictionary
4. Create corresponding DataForge domains

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test research (requires DataForge)
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "genre": "general"}'

# Test brainstorming
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test idea", "genre": "fantasy", "num_ideas": 3}'
```

## 🔧 Troubleshooting

### 1. "ANTHROPIC_API_KEY environment variable is required"

**Cause:** Missing or invalid Anthropic API key in environment.

**Solution:**

```bash
# Get API key from https://console.anthropic.com/
# Add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env

# Verify it's loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Key loaded!' if os.getenv('ANTHROPIC_API_KEY') else 'Key missing!')"

# Restart AuthorForge
uvicorn app.main:app --reload --port 8000
```

### 2. "Failed to connect to DataForge"

**Cause:** DataForge not running or incorrect URL configuration.

**Solution:**

```bash
# Check if DataForge is running
curl http://localhost:8001/health

# If not running, start it
cd ../DataForge
source venv/bin/activate
uvicorn app.main:app --port 8001

# Verify configuration in AuthorForge .env
cat .env | grep DATAFORGE_URL
# Should show: DATAFORGE_URL=http://localhost:8001

# Test connection
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "genre": "general"}'
```

### 3. No research results returned

**Cause:** DataForge has no documents in genre-specific domains.

**Solution:**

```bash
# Check DataForge document count
curl http://localhost:8001/api/search/stats

# Check specific domain
curl http://localhost:8001/api/documents/domain/fantasy_craft

# Upload documents to DataForge
cd ../DataForge
python scripts/upload_documents.py --domain fantasy_craft --path ~/writing_library/

# Try broader search terms in AuthorForge
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{"query": "character", "genre": "general", "max_results": 10}'
```

### 4. Slow API response times

**Cause:** Large DataForge queries or slow Anthropic API.

**Solution:**

```bash
# Reduce max_results in queries
# Instead of max_results: 10, use max_results: 5

# Check DataForge performance
curl http://localhost:8001/api/search/benchmark

# Enable caching in AuthorForge (add to .env)
echo "ENABLE_CACHE=true" >> .env
echo "CACHE_TTL=300" >> .env  # 5 minutes

# Monitor response times
curl -w "\nTime: %{time_total}s\n" \
  -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "genre": "general"}'
```

### 5. "Invalid genre specified"

**Cause:** Using incorrect genre identifier in API calls.

**Solution:**

```bash
# Valid genres (case-sensitive):
# - fantasy
# - scifi
# - christian_fiction
# - general

# Check available genres
curl http://localhost:8000/api/genres

# Use correct genre in request
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "genre": "fantasy"}'  # lowercase, no spaces
```

### 6. Brainstorming returns generic ideas

**Cause:** Insufficient context or vague prompt.

**Solution:**

```bash
# Provide detailed, specific prompts
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A colony ship carrying 10,000 settlers discovers an ancient alien artifact that appears to be a quantum computer capable of simulating entire universes",
    "genre": "scifi",
    "num_ideas": 5
  }'

# Use genre-specific language
# Fantasy: mention magic, realms, ancient prophecies
# Sci-Fi: mention technology, future societies, space
# Christian: mention faith, redemption, spiritual journeys
```

### 7. Import errors on startup

**Cause:** Missing dependencies or incorrect Python version.

**Solution:**

```bash
# Verify Python version
python --version  # Should be 3.11+

# Reinstall dependencies
cd AuthorForge
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# If still failing, check specific import
python -c "from anthropic import Anthropic; print('Anthropic OK')"
python -c "from fastapi import FastAPI; print('FastAPI OK')"
```

### 8. Port 8000 already in use

**Cause:** Another service running on port 8000.

**Solution:**

```bash
# Find process using port 8000
lsof -i :8000
# or
netstat -tuln | grep 8000

# Kill the process (replace PID)
kill -9 <PID>

# Or use different port
uvicorn app.main:app --reload --port 8002

# Update .env if using different port
echo "PORT=8002" >> .env
```

### 9. CORS errors in browser

**Cause:** Frontend trying to access API from different origin.

**Solution:**

```bash
# Add CORS origins to .env
echo 'CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]' >> .env

# Or allow all origins in development (not recommended for production)
echo 'CORS_ORIGINS=["*"]' >> .env

# Restart server
uvicorn app.main:app --reload --port 8000
```

### 10. NeuroForge integration not working

**Cause:** NeuroForge not configured or not running.

**Solution:**

```bash
# NeuroForge is optional - AuthorForge uses Claude directly by default
# To enable NeuroForge:
echo "USE_NEUROFORGE=true" >> .env
echo "NEUROFORGE_URL=http://localhost:8002" >> .env

# Verify NeuroForge is running
curl http://localhost:8002/health

# Test NeuroForge integration
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "genre": "general", "use_neuroforge": true}'
```

## 🚀 Deployment

### Production Environment Variables

Complete `.env` configuration for production:

```bash
# Core Configuration
ANTHROPIC_API_KEY=sk-ant-your-production-key
DATAFORGE_URL=https://dataforge.yourapp.com
PORT=8000

# Security
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=["https://yourapp.com","https://www.yourapp.com"]
ALLOWED_HOSTS=["authorforge.yourapp.com"]

# Performance
MAX_WORKERS=4
TIMEOUT=60
KEEPALIVE_TIMEOUT=5

# Caching (optional)
ENABLE_CACHE=true
CACHE_TTL=300
REDIS_URL=redis://localhost:6379/0

# NeuroForge Integration (optional)
USE_NEUROFORGE=true
NEUROFORGE_URL=https://neuroforge.yourapp.com

# Monitoring (optional)
SENTRY_DSN=https://your-sentry-dsn
ENABLE_METRICS=true
METRICS_PORT=9090
```

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 authorforge && \
    chown -R authorforge:authorforge /app

USER authorforge

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**docker-compose.yml:**

```yaml
version: "3.8"

services:
  authorforge:
    build: .
    container_name: authorforge
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATAFORGE_URL=http://dataforge:8001
      - DEBUG=false
      - LOG_LEVEL=INFO
    depends_on:
      - dataforge
    networks:
      - forge-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  dataforge:
    image: dataforge:latest
    container_name: dataforge
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/dataforge
    depends_on:
      - postgres
    networks:
      - forge-network
    restart: unless-stopped

  postgres:
    image: pgvector/pgvector:pg16
    container_name: postgres
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=dataforge
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - forge-network
    restart: unless-stopped

networks:
  forge-network:
    driver: bridge

volumes:
  postgres-data:
```

**Build and run:**

```bash
# Build image
docker build -t authorforge:latest .

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f authorforge

# Scale workers
docker-compose up -d --scale authorforge=3
```

### Production Checklist

- [ ] Set strong `ANTHROPIC_API_KEY` in production environment
- [ ] Configure proper `CORS_ORIGINS` (no wildcards)
- [ ] Set `DEBUG=false` and `LOG_LEVEL=INFO`
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Set up database backups (DataForge PostgreSQL)
- [ ] Configure monitoring and alerting (Sentry, Datadog)
- [ ] Implement rate limiting on API endpoints
- [ ] Set up log aggregation (ELK stack, CloudWatch)
- [ ] Configure health checks and auto-restart
- [ ] Use secrets management (AWS Secrets Manager, Vault)
- [ ] Set resource limits (CPU, memory) in production
- [ ] Enable request/response compression
- [ ] Configure CDN for static assets (if any)
- [ ] Set up CI/CD pipeline for automated deployment
- [ ] Document rollback procedures

### Platform-Specific Deployment

**AWS ECS:**

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag authorforge:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/authorforge:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/authorforge:latest

# Deploy to ECS (requires task definition)
aws ecs update-service --cluster forge-cluster --service authorforge --force-new-deployment
```

**Heroku:**

```bash
# Create app
heroku create authorforge-prod

# Set environment variables
heroku config:set ANTHROPIC_API_KEY=sk-ant-your-key
heroku config:set DATAFORGE_URL=https://dataforge-prod.herokuapp.com

# Deploy
git push heroku main

# Check logs
heroku logs --tail
```

**DigitalOcean App Platform:**

```yaml
# app.yaml
name: authorforge
services:
  - name: api
    dockerfile_path: Dockerfile
    source_dir: /
    github:
      repo: your-org/authorforge
      branch: main
    envs:
      - key: ANTHROPIC_API_KEY
        scope: RUN_TIME
        value: ${ANTHROPIC_API_KEY}
      - key: DATAFORGE_URL
        scope: RUN_TIME
        value: ${DATAFORGE_URL}
    health_check:
      http_path: /health
    http_port: 8000
    instance_count: 2
    instance_size_slug: basic-xs
```

## 🔗 Quick Links

### Essential Resources

- **📚 API Documentation**: http://localhost:8000/docs (interactive OpenAPI docs)
- **🏥 Health Check**: http://localhost:8000/health
- **📊 API Stats**: http://localhost:8000/api/stats
- **🔍 Research Endpoint**: http://localhost:8000/research/query
- **💡 Brainstorm Endpoint**: http://localhost:8000/smithy/brainstorm

### Related Documentation

- **DataForge README**: [../DataForge/README.md](../DataForge/README.md)
- **DataForge API Docs**: http://localhost:8001/docs
- **NeuroForge README**: [../NeuroForge/README.md](../NeuroForge/README.md)
- **VibeForge README**: [../vibeforge/README.md](../vibeforge/README.md)

### Example Requests

**Quick Research Test:**

```bash
curl -X POST http://localhost:8000/research/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I write compelling dialogue?", "genre": "general", "max_results": 3}'
```

**Quick Brainstorm Test:**

```bash
curl -X POST http://localhost:8000/smithy/brainstorm \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A detective discovers magic is real", "genre": "fantasy", "num_ideas": 5}'
```

**Health Check:**

```bash
curl http://localhost:8000/health | jq .
```

### Support Contacts

- **Technical Support**: charlesboswell@boswelldigitalsolutions.com
- **Commercial Licensing**: charles@birradat.com
- **Bug Reports**: [GitHub Issues](https://github.com/Boswecw/DataForge/issues)

---

## 📄 License

**Commercial License - All Rights Reserved**

AuthorForge is commercial software. This code is provided for evaluation and integration purposes only.

### Terms

- **Permitted**: Evaluation, internal testing, integration with authorized Forge Suite products
- **Prohibited**: Redistribution, modification, commercial use without license, reverse engineering
- **Intellectual Property**: All algorithms, genre models, writing strategies, and business logic are proprietary and protected

### Licensing

For commercial licensing, enterprise agreements, or integration with AuthorForge:

**Birradat Software** (BDS)  
Contact: charles@birradat.com  
Web: https://birradat.com

### Copyright

© 2025 Birradat Software. All rights reserved.

---

**AuthorForge** - Cathedral-level AI writing platform for creative professionals ✨📖
