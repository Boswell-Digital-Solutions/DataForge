# AuthorForge Backend

> AI-Powered Writing Assistant API for Fantasy, Sci-Fi, and Christian Fiction

**AuthorForge** is a FastAPI application that provides AI-powered writing assistance with genre-aware brainstorming, research, and synthesis capabilities. It integrates with [DataForge](../DataForge/) for knowledge base search and uses Claude AI for content generation.

## Features

- **Multi-Genre Support**: Fantasy, Sci-Fi, Christian Fiction, and General writing
- **Research Assistant**: AI-synthesized answers from your knowledge base
- **Smithy Brainstorming**: Generate and expand story ideas
- **Genre-Aware Prompts**: Tailored AI responses for each genre
- **DataForge Integration**: Semantic search of your writing craft knowledge

## Supported Genres

### Fantasy
- Magic system design
- Worldbuilding and mythology
- Epic storytelling
- Fantasy-specific knowledge base

### Sci-Fi
- Technology and science concepts
- Future society worldbuilding
- Space opera and hard sci-fi
- Scientific accuracy guidance

### Christian Fiction
- Biblical themes and parallels
- Spiritual journey arcs
- Faith integration in narrative
- Scripture connections

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

| Genre | DataForge Domains |
|-------|-------------------|
| Fantasy | fantasy_craft, worldbuilding, writing_craft |
| Sci-Fi | scifi_craft, worldbuilding, writing_craft |
| Christian Fiction | christian_fiction_craft, biblical_themes, writing_craft |
| General | writing_craft |

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

## Troubleshooting

### "ANTHROPIC_API_KEY environment variable is required"

**Solution:**
1. Get key from https://console.anthropic.com/
2. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### "Failed to connect to DataForge"

**Solution:**
1. Ensure DataForge is running: `curl http://localhost:8001/health`
2. Check `DATAFORGE_URL` in `.env`
3. Verify no firewall blocking port 8001

### No research results

**Solution:**
1. Ensure DataForge has documents: `curl http://localhost:8001/api/search/stats`
2. Check that domains exist in DataForge
3. Try broader search terms

## Deployment

### Environment Variables for Production

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-your-production-key
DATAFORGE_URL=https://dataforge.yourapp.com
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourapp.com
```

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## License

MIT License

---

**AuthorForge** - Genre-aware AI assistance for writers ✨📖
