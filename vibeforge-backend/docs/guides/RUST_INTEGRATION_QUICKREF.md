# VibeForge Python-Rust Integration — Quick Reference

## Installation & Setup

```bash
# Clone and setup
cd vibeforge-backend
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]

# Build the Rust extension
maturin develop
```

## Common Commands

### Building

| Command                     | Purpose                                      |
| --------------------------- | -------------------------------------------- |
| `maturin develop`           | Build and install extension (dev mode, fast) |
| `maturin develop --release` | Build with optimizations                     |
| `maturin build`             | Build wheel for distribution                 |
| `./build_rust.sh develop`   | Build script (same as maturin develop)       |
| `./build_rust.sh release`   | Build with all optimizations                 |
| `./build_rust.sh test`      | Build and run comprehensive tests            |
| `./build_rust.sh clean`     | Remove all build artifacts                   |

### Testing & Verification

| Command                                                    | Purpose                |
| ---------------------------------------------------------- | ---------------------- |
| `python3 demo_vibeforge_prompt.py`                         | Run full demonstration |
| `./build_rust.sh test`                                     | Run automated tests    |
| `python3 -c "from vibeforge_prompt import *; print('OK')"` | Quick import check     |

## Using the Extension

### Basic Usage

```python
from vibeforge_prompt import (
    build_prompt,
    estimate_tokens,
    estimate_tokens_precise,
    build_initial_run,
    estimate_tokens_for_prompt,
    PromptContext,
)

# Quick token count
tokens = estimate_tokens("Your text here")  # ~1 microsecond

# Build combined prompt
prompt = build_prompt(
    contexts=["System context", "Code guidelines"],
    prompt="Your question"
)

# Precise token count
precise_tokens = estimate_tokens_precise(prompt)

# Create run record
import json
run_json = build_initial_run("gpt-4", "Your prompt")
run_data = json.loads(run_json)
```

### PromptContext (Stateful)

```python
ctx = PromptContext("System", "User question")
ctx.add_context("Context 1")
ctx.add_context("Context 2")
merged = ctx.merge_contexts()
ctx.recalculate_tokens()
print(ctx.total_tokens_estimated)
```

## API Reference

### Functions

#### `estimate_tokens(text: str) -> int`

- Naive token estimation: ~4 characters = 1 token
- Very fast (~1 µs)
- Use for quick estimates

#### `estimate_tokens_precise(text: str) -> int`

- Word-count based with punctuation adjustment
- More accurate (~10 µs)
- Use when accuracy matters

#### `build_prompt(contexts: List[str], prompt: str) -> str`

- Combines contexts and user prompt with markdown structure
- Returns complete formatted prompt string
- Output structure:

  ```
  # Context Information

  Context 1
  ---
  Context 2
  ---

  # Task

  User prompt
  ```

#### `estimate_tokens_for_prompt(contexts: List[str], prompt: str) -> int`

- Builds prompt and estimates tokens
- Convenience function combining build_prompt + estimate_tokens_precise
- Best for final token count before API call

#### `build_initial_run(model: str, prompt: str) -> str`

- Creates JSON run record with UUID, timestamp, status
- Returns JSON string (not parsed)
- Result fields: id, model, prompt, status, created_at, timestamps, duration_ms

### Classes

#### `PromptContext(system_prompt: str, user_prompt: str)`

- Stateful context management
- Methods:
  - `add_context(text: str)`: Add context block, updates tokens
  - `merge_contexts() -> str`: Get merged full prompt
  - `recalculate_tokens()`: Recompute token count
- Properties:
  - `system_prompt`: Initial system prompt
  - `user_prompt`: User's question/task
  - `context_blocks`: List of added contexts
  - `total_tokens_estimated`: Current token count

## Typical Workflow

```python
# 1. In your API endpoint
from fastapi import APIRouter
from vibeforge_prompt import build_prompt, estimate_tokens_for_prompt

@router.post("/v1/vibeforge/run")
async def create_run(request: CreateRunRequest):
    # Build prompt from contexts and user input
    final_prompt = build_prompt(
        contexts=fetch_contexts(request.context_ids),
        prompt=request.prompt
    )

    # Estimate tokens
    token_count = estimate_tokens_for_prompt(
        contexts=fetch_contexts(request.context_ids),
        prompt=request.prompt
    )

    # Check budget
    if token_count > request.max_tokens:
        raise HTTPException(400, "Prompt too large")

    # Call LLM with built prompt
    response = await llm_service.call(
        model=request.model,
        prompt=final_prompt,
        tokens_estimate=token_count
    )

    return ModelRunResponse(...)
```

## File Locations

| File                           | Purpose                                      |
| ------------------------------ | -------------------------------------------- |
| `pyproject.toml`               | Maturin config, defines module name and path |
| `rust/forge_prompt/src/lib.rs` | Rust source with all functions               |
| `rust/forge_prompt/Cargo.toml` | Rust dependencies                            |
| `build_rust.sh`                | Build automation (optional)                  |
| `demo_vibeforge_prompt.py`     | Live demonstration script                    |
| `BUILD_INSTRUCTIONS.md`        | Detailed build guide                         |

## Platform-Specific Extensions

After build, you'll have:

- **Linux**: `.so` file in site-packages
- **macOS**: `.dylib` file in site-packages
- **Windows**: `.pyd` file in site-packages

Location: Check with `python3 -c "import vibeforge_prompt; print(vibeforge_prompt.__file__)"`

## Troubleshooting

| Problem                | Solution                                                              |
| ---------------------- | --------------------------------------------------------------------- |
| ModuleNotFoundError    | Run `maturin develop`                                                 |
| Import takes long time | Normal on first import, use `--release`                               |
| Build fails            | Run `cargo clean` in rust/forge_prompt, then rebuild                  |
| Wrong Python version   | Check `python3 --version` matches `requires-python` in pyproject.toml |

## Performance Tips

1. **Reuse PromptContext** for similar workflows
2. **Use estimate_tokens()** for quick estimates
3. **Use estimate_tokens_precise()** only when accuracy critical
4. **Batch operations** where possible
5. **Cache** built prompts if templates don't change

## Configuration

Edit `pyproject.toml` to change module behavior:

```toml
[tool.maturin]
module-name = "vibeforge_prompt"      # Change this to rename module
manifest-path = "rust/forge_prompt/Cargo.toml"
features = ["pyo3/extension-module"]   # Required for Python
```

## Integration Checklist

- [ ] Build successful: `maturin develop`
- [ ] Import works: `from vibeforge_prompt import *`
- [ ] Demo runs: `python3 demo_vibeforge_prompt.py`
- [ ] Tests pass: `./build_rust.sh test`
- [ ] FastAPI routers import the functions
- [ ] Token estimation integrated in create_run endpoint
- [ ] Prompt building used before LLM calls
- [ ] Error handling for large prompts

## Next Steps

1. **Integrate with routers**: Use in `app/routers/vibeforge.py`
2. **Add to LLM service**: Update `app/services/llm_service.py`
3. **Create tests**: Add `tests/test_vibeforge_prompt.py`
4. **Deploy**: Build wheels for target platforms
5. **Monitor**: Track token usage and build performance metrics

---

**More info**: See `BUILD_INSTRUCTIONS.md` for detailed documentation
