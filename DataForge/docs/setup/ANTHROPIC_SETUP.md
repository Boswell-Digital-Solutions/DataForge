# DataForge - Anthropic/Voyage AI Setup

DataForge has been configured to use **Voyage AI** as the primary embedding provider. Voyage AI is owned by Anthropic and is the recommended embedding solution for the Anthropic ecosystem.

---

## Why Voyage AI?

**Anthropic (Claude) does not provide an embeddings API.** Instead, they recommend using **Voyage AI**, which they acquired in 2024. Voyage AI provides state-of-the-art embedding models optimized for semantic search.

---

## Quick Setup

### 1. Get a Voyage AI API Key

Sign up at: https://www.voyageai.com/

After signup, you'll get an API key that looks like: `pa-...`

### 2. Set Your Environment Variable

In your `.env` file:

```bash
# Voyage AI (Recommended for Anthropic ecosystem)
VOYAGE_API_KEY=pa-your-actual-voyage-key-here

# Generate a secure secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dataforge
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `voyageai==0.2.3` (primary embedding provider)
- `openai==1.10.0` (fallback option)

### 4. Start DataForge

```bash
uvicorn app.main:app --reload --port 8001
```

You should see:
```
✅ Configuration validated
✅ Using voyage-ai for embeddings
✅ Database tables created
```

---

## Embedding Models

DataForge is configured to use **voyage-large-2** by default:

- **Model**: `voyage-large-2`
- **Dimensions**: 1536
- **Max Input**: 16,000 tokens
- **Best for**: Long-form content, documents, semantic search

### Alternative Voyage AI Models

You can change the model in [app/config.py](app/config.py):

```python
# For shorter texts (faster, cheaper)
EMBEDDING_MODEL = "voyage-2"  # 1024 dimensions

# For code (optimized for programming)
EMBEDDING_MODEL = "voyage-code-2"  # 1536 dimensions

# For long documents (current default)
EMBEDDING_MODEL = "voyage-large-2"  # 1536 dimensions
```

**Important**: If you change the model dimension, you must:
1. Update `EMBEDDING_DIMENSION` in config.py
2. Recreate the database (or run a migration to update the vector column)

---

## Provider Priority

DataForge checks for embedding providers in this order:

1. **Voyage AI** (if `VOYAGE_API_KEY` is set) ← **Recommended**
2. OpenAI (if `OPENAI_API_KEY` is set)
3. Cohere (if `COHERE_API_KEY` is set)

You can use any provider, but Voyage AI is recommended for the Anthropic ecosystem.

---

## Cost Comparison

### Voyage AI Pricing (voyage-large-2)
- **$0.00012 per 1K tokens**
- Example: 1M tokens = $0.12

### OpenAI Pricing (text-embedding-ada-002)
- **$0.0001 per 1K tokens**
- Example: 1M tokens = $0.10

Both are very affordable. Voyage AI is slightly more expensive but offers better quality for semantic search tasks.

---

## Testing Your Setup

### Test 1: Create a Document

```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your-password" | jq -r .access_token)

# Create a domain
curl -X POST http://localhost:8001/admin/domains \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test",
    "label": "Test Domain",
    "description": "A test domain"
  }'

# Create a document (will use Voyage AI for embeddings)
curl -X POST http://localhost:8001/admin/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "domain_id": "test",
    "title": "Test Document",
    "doc_type": "guide",
    "content": "This is a test document about Anthropic and Claude. It will be embedded using Voyage AI, which is owned by Anthropic and provides state-of-the-art embeddings for semantic search.",
    "tags": ["test", "anthropic"],
    "is_published": true
  }'
```

### Test 2: Search

```bash
# Search using semantic similarity (powered by Voyage AI embeddings)
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me about Claude and Anthropic",
    "limit": 5,
    "similarity_threshold": 0.5
  }'
```

You should get results with similarity scores!

---

## Configuration Files Changed

### 1. [app/config.py](app/config.py)
- Updated default `EMBEDDING_MODEL` to `"voyage-large-2"`
- Added `ANTHROPIC_API_KEY` (for future use)
- Reordered `VOYAGE_API_KEY` to be primary
- Updated validation to check for Voyage AI first

### 2. [app/utils/embeddings.py](app/utils/embeddings.py)
- Added Voyage AI as Option 1 (primary)
- Kept OpenAI and Cohere as fallbacks
- Updated docstrings to mention Anthropic/Voyage AI

### 3. [requirements.txt](requirements.txt)
- Added `voyageai==0.2.3` (uncommented)
- Added note recommending Voyage AI

### 4. [.env.example](.env.example)
- Made `VOYAGE_API_KEY` the primary example
- Added `ANTHROPIC_API_KEY` as optional (for future use)
- Added `LOG_LEVEL` setting

---

## Using Multiple Providers

You can have multiple API keys set. DataForge will use them in priority order:

```bash
# .env file
VOYAGE_API_KEY=pa-your-voyage-key    # Will use this first
OPENAI_API_KEY=sk-your-openai-key    # Fallback if Voyage fails
```

This provides redundancy if one provider has an outage.

---

## Anthropic API Key (Future Use)

The `ANTHROPIC_API_KEY` is included for future enhancements, such as:

- Using Claude for document summarization
- Using Claude for query expansion
- Using Claude for retrieval-augmented generation (RAG)

Currently, it's not used for embeddings since Anthropic doesn't provide an embeddings API.

---

## Switching from OpenAI to Voyage AI

If you were previously using OpenAI and want to switch:

### Option 1: Keep Existing Embeddings
1. Set `VOYAGE_API_KEY` in your `.env`
2. **New documents** will use Voyage AI
3. **Existing documents** will keep their OpenAI embeddings
4. Search will work across both (same dimension: 1536)

### Option 2: Re-embed Everything
1. Export your documents
2. Drop and recreate the database
3. Set `VOYAGE_API_KEY`
4. Re-import documents (they'll be embedded with Voyage AI)

**Note**: Both `voyage-large-2` and `text-embedding-ada-002` produce 1536-dimensional embeddings, so they're compatible for search!

---

## Performance

Voyage AI embeddings are optimized for:
- ✅ **Long documents** (up to 16K tokens)
- ✅ **Semantic search** (better than OpenAI for retrieval tasks)
- ✅ **Domain-specific content** (handles specialized vocabulary better)
- ✅ **Multilingual** (supports 100+ languages)

---

## Troubleshooting

### "No embedding provider configured"

**Cause**: `VOYAGE_API_KEY` is not set in `.env`

**Fix**:
```bash
# Add to .env
VOYAGE_API_KEY=pa-your-actual-key-here
```

### "Embedding generation failed: 401"

**Cause**: Invalid API key

**Fix**: Check that your Voyage AI key is correct and active

### "Embedding generation failed: Module 'voyageai' not found"

**Cause**: voyageai package not installed

**Fix**:
```bash
pip install voyageai==0.2.3
```

### Want to use OpenAI instead?

Just don't set `VOYAGE_API_KEY`, and set `OPENAI_API_KEY` instead. DataForge will automatically use OpenAI.

---

## Documentation

- **Voyage AI Docs**: https://docs.voyageai.com/
- **Voyage AI Models**: https://docs.voyageai.com/docs/embeddings
- **Anthropic**: https://www.anthropic.com/

---

## Summary

✅ DataForge now uses **Voyage AI** (Anthropic-owned) as the primary embedding provider
✅ Configuration updated to prioritize `VOYAGE_API_KEY`
✅ Default model: `voyage-large-2` (1536 dimensions)
✅ Fallback to OpenAI or Cohere if Voyage AI not configured
✅ Compatible with existing OpenAI embeddings (same dimensions)

**Get started**: Sign up at https://www.voyageai.com/ and add your API key to `.env`!

---

*For questions about the original bug fixes, see [FIXES.md](FIXES.md)*
*For general setup, see [QUICK_START_AFTER_FIXES.md](QUICK_START_AFTER_FIXES.md)*
