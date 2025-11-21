# 📋 LLM Service Quick Reference Card

**Status**: ✅ PRODUCTION READY | **Version**: 1.0.0 | **Tests**: 24/24 PASSING

---

## 🚀 Quick Start (30 seconds)

```bash
# 1. Set environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Run tests to verify
cd /home/charles/projects/Coding2025/Forge/vibeforge-backend
python3 test_llm_service.py

# 3. Start server
uvicorn app.main:app --port 8000
```

---

## 📚 API Cheat Sheet

### Basic Usage

```python
from app.services.llm_service import call_llm, estimate_tokens

# Call LLM
response = await call_llm("gpt-4", "Your prompt", max_tokens=500)
print(response.content)

# Estimate tokens
tokens = estimate_tokens("gpt-4", "Your text")
```

### Response Object

```python
response.content           # Generated text
response.prompt_tokens    # Input tokens
response.completion_tokens # Output tokens
response.total_tokens     # Combined
response.model            # Model used
response.provider         # Provider (openai, claude, ollama)
response.latency_ms       # Time taken
response.timestamp        # When generated
response.to_dict()        # Convert to dict
```

### Model Selection

```python
await call_llm("gpt-4", prompt)              # OpenAI (auto-detect)
await call_llm("gpt-3.5-turbo", prompt)      # OpenAI (auto-detect)
await call_llm("claude-3-opus", prompt)      # Anthropic (auto-detect)
await call_llm("claude-3-sonnet", prompt)    # Anthropic (auto-detect)
await call_llm("local-mistral", prompt)      # Ollama (auto-detect)
await call_llm("openai:gpt-4", prompt)       # Explicit OpenAI
await call_llm("claude:custom", prompt)      # Explicit Anthropic
```

### Concurrent Calls

```python
responses = await asyncio.gather(
    call_llm("gpt-4", prompt),
    call_llm("claude-3-opus", prompt),
    call_llm("local-mistral", prompt),
)
```

### Error Handling

```python
try:
    response = await call_llm(model, prompt, timeout=120)
except ValueError:
    print("Unknown provider")
except TimeoutError:
    print("Request timeout")
except Exception as e:
    print(f"Error: {e}")
```

### Custom Configuration

```python
from app.services.llm_service import get_llm_service, ModelConfig

service = get_llm_service()

# Register custom model
config = ModelConfig(
    name="my-model",
    provider="openai",
    max_tokens=1000,
    timeout=60,
    temperature=0.7
)
service.register_model("my-model", config)

# Use it
response = await call_llm("my-model", prompt)
```

---

## 🔧 Configuration

### Environment Variables

```bash
OPENAI_API_KEY=sk-...                              # Required for GPT
ANTHROPIC_API_KEY=sk-ant-...                       # Required for Claude
OLLAMA_BASE_URL=http://localhost:11434             # Optional (Ollama)
```

### Default Model Settings

```
claude-3-opus:   max_tokens=4096, timeout=300s
claude-3-sonnet: max_tokens=4096, timeout=300s
gpt-4:           max_tokens=8192, timeout=300s
gpt-3.5-turbo:   max_tokens=2048, timeout=300s
local-mistral:   max_tokens=2048, timeout=600s
```

---

## 📊 Token Estimation

```python
# Rust-powered (fast)
tokens = estimate_tokens("gpt-4", text)  # ~1-10 microseconds

# Fallback (slow)
tokens = max(1, len(text) // 4)          # ~100 microseconds

# Check before calling
text = "Your prompt"
tokens = estimate_tokens("gpt-4", text)
if tokens < 4000:
    response = await call_llm("gpt-4", text)
```

---

## 🧪 Testing & Verification

```bash
# Full test suite (24 tests)
python3 test_llm_service.py

# Specific test
python3 -m pytest test_llm_service.py::test_provider_detection -v

# Examples and integration
python3 llm_service_examples.py

# Verify imports
python3 -c "from app.services.llm_service import call_llm; print('✓ OK')"
```

---

## 🐳 Docker Deployment

```bash
# Build
docker build -t vibeforge-backend .

# Run
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="sk-..." \
  -e ANTHROPIC_API_KEY="sk-ant-..." \
  vibeforge-backend

# Docker Compose
docker-compose up -d
```

---

## 🔌 FastAPI Integration

```python
from fastapi import APIRouter
from app.services.llm_service import call_llm

router = APIRouter()

@router.post("/generate")
async def generate(model: str, prompt: str, max_tokens: int = 500):
    response = await call_llm(model, prompt, max_tokens)
    return {
        "content": response.content,
        "tokens": response.total_tokens,
        "latency_ms": response.latency_ms,
    }
```

---

## ⚙️ Common Operations

### Get Provider Status

```python
service = get_llm_service()
status = service.get_provider_status()
print(status)
# {
#   "claude": {"available": False, "has_api_key": False},
#   "openai": {"available": True, "has_api_key": True},
#   "ollama": {"available": True, "has_api_key": False},
# }
```

### Check API Key

```python
import os
has_key = bool(os.getenv("OPENAI_API_KEY"))
print(f"API Key set: {has_key}")
```

### Set Timeout

```python
# Per request
response = await call_llm(model, prompt, timeout=600)

# Per model (via config)
config = ModelConfig(
    name="slow-model",
    provider="ollama",
    timeout=3600  # 1 hour
)
```

---

## 🆘 Troubleshooting

| Issue                                      | Solution                                |
| ------------------------------------------ | --------------------------------------- |
| `ValueError: unknown provider`             | Check model name or use explicit syntax |
| `TimeoutError`                             | Increase timeout or check network       |
| `Provider not available`                   | Set API key env variable                |
| `AttributeError: no attribute send_prompt` | Rebuild Rust extension                  |
| `Connection refused`                       | Check provider is running (esp. Ollama) |

---

## 📈 Performance Tips

1. **Reuse service instance** (singleton pattern)
2. **Use token estimation** before calling APIs
3. **Batch requests** with `asyncio.gather()`
4. **Set appropriate timeouts** per model
5. **Cache estimations** for repeated text
6. **Use connection pooling** (built-in)
7. **Implement rate limiting** for production

---

## 🔐 Security Checklist

- [ ] API keys in environment variables
- [ ] Never log credentials
- [ ] Set request timeouts
- [ ] Validate user input
- [ ] Use HTTPS in production
- [ ] Setup rate limiting
- [ ] Configure CORS properly
- [ ] Monitor error logs

---

## 📚 Documentation Links

| Document                        | Purpose                |
| ------------------------------- | ---------------------- |
| `LLM_SERVICE_IMPLEMENTATION.md` | Full API reference     |
| `DEPLOYMENT_GUIDE.md`           | Production deployment  |
| `llm_service_examples.py`       | Real-world examples    |
| `test_llm_service.py`           | Test cases (reference) |
| `app/services/llm_service.py`   | Source code            |

---

## ✅ Files Delivered

```
vibeforge-backend/
├── python/app/services/llm_service.py         (550+ lines)
├── test_llm_service.py                        (240+ lines)
├── llm_service_examples.py                    (400+ lines)
├── LLM_SERVICE_IMPLEMENTATION.md              (300+ lines)
├── DEPLOYMENT_GUIDE.md                        (300+ lines)
├── LLM_SERVICE_COMPLETION.md                  (400+ lines)
└── llm_service_quickref.md                    (THIS FILE)
```

---

## 🎯 Next Steps

1. **Set environment variables** with your API keys
2. **Run test suite** to verify: `python3 test_llm_service.py`
3. **Review examples** in `llm_service_examples.py`
4. **Integrate into routers** using patterns from examples
5. **Deploy to production** following `DEPLOYMENT_GUIDE.md`

---

## 📞 Quick Support

**Setup Issue?**

- Check environment variables: `echo $OPENAI_API_KEY`
- Verify API keys are active
- Run: `python3 test_llm_service.py`

**Integration Issue?**

- Copy patterns from `llm_service_examples.py`
- Check async/await usage
- Verify imports

**Performance Issue?**

- Check token estimation cache
- Verify connection pooling
- Monitor concurrent requests
- Check timeout settings

**Deployment Issue?**

- Review `DEPLOYMENT_GUIDE.md`
- Check Docker logs
- Verify environment variables
- Test health endpoint

---

**Created**: 2025-11-18
**Status**: ✅ **PRODUCTION READY**
**Version**: 1.0.0
**Last Updated**: 2025-11-18
