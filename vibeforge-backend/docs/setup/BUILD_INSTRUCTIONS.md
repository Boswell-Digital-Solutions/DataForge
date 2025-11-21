# Python-Rust Integration: Building the vibeforge_prompt Extension

This document explains how to build and use the `vibeforge_prompt` Rust extension module for VibeForge.

## Overview

The project uses **Maturin** to compile Rust code (using PyO3) into Python extension modules. The extension module `vibeforge_prompt` provides high-performance functions for:

- Token estimation (naive and precise methods)
- Prompt building from contexts and user input
- Initial run record creation
- Stateful prompt context management

## Prerequisites

1. **Python 3.10+** installed and available as `python3`
2. **Rust toolchain** (install from https://rustup.rs/)
3. **Virtual environment** (recommended)

## Quick Start

### 1. Set up Virtual Environment

```bash
cd /path/to/vibeforge-backend
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -e .[dev]
```

This installs:

- FastAPI, Pydantic, Uvicorn (Python runtime)
- pytest, pytest-asyncio, httpx (testing)
- maturin (Rust-Python build tool)

### 3. Build the Extension

```bash
# Development build (faster, with debug symbols)
maturin develop

# Or use the provided script
./build_rust.sh develop
```

### 4. Verify Installation

```bash
python3 -c "from vibeforge_prompt import build_prompt; print('✓ Extension loaded successfully')"
```

### 5. Run Demo

```bash
python3 demo_vibeforge_prompt.py
```

## Build Commands

### Using Maturin Directly

```bash
# Development mode (fast compile, installs in active venv)
maturin develop

# Development mode with optimizations
maturin develop --release

# Build wheel distribution (outputs to dist/)
maturin build

# Build release wheel
maturin build --release
```

### Using the Build Script

```bash
./build_rust.sh develop      # Development build
./build_rust.sh release      # Release build with optimizations
./build_rust.sh build        # Build wheel
./build_rust.sh clean        # Clean build artifacts
./build_rust.sh test         # Build and run tests
```

## File Structure

```
vibeforge-backend/
├── pyproject.toml                 # Maturin configuration
├── rust/
│   ├── Cargo.toml                # Workspace root
│   └── forge_prompt/
│       ├── Cargo.toml            # forge_prompt crate (points to vibeforge_prompt module)
│       └── src/
│           └── lib.rs            # Rust source with PyO3 decorators
├── build_rust.sh                 # Build automation script
├── demo_vibeforge_prompt.py       # Demonstration script
└── python/
    └── app/
        └── ...
```

## Key Configuration Files

### pyproject.toml

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[tool.maturin]
module-name = "vibeforge_prompt"      # Python module name
python-source = "python"              # Python code location
manifest-path = "rust/forge_prompt/Cargo.toml"
features = ["pyo3/extension-module"]
```

**Key settings:**

- `module-name`: The name of the Python module (what you import with `from vibeforge_prompt import ...`)
- `manifest-path`: Path to the specific Cargo.toml to build
- `features`: Enables PyO3 extension module support

### rust/forge_prompt/Cargo.toml

```toml
[lib]
name = "forge_prompt"
crate-type = ["cdylib"]  # C-compatible dynamic library (required for Python)
```

**Key settings:**

- `crate-type = ["cdylib"]`: Compiles to `.so` (Linux), `.pyd` (Windows), or `.dylib` (macOS)

## Usage Examples

### Import and Use Functions

```python
from vibeforge_prompt import (
    build_prompt,
    estimate_tokens,
    estimate_tokens_precise,
    build_initial_run,
    estimate_tokens_for_prompt,
    PromptContext,
)

# Estimate tokens quickly
text = "Hello, world!"
tokens = estimate_tokens(text)  # Returns int

# Build a combined prompt
contexts = ["Context 1", "Context 2"]
user_prompt = "Do something"
full_prompt = build_prompt(contexts, user_prompt)

# Get precise token count for built prompt
total_tokens = estimate_tokens_for_prompt(contexts, user_prompt)

# Create a run record (returns JSON string)
import json
run_json = build_initial_run("gpt-4", user_prompt)
run_data = json.loads(run_json)
print(run_data["id"])  # UUID
```

### Use PromptContext Class

```python
from vibeforge_prompt import PromptContext

# Initialize with system and user prompts
ctx = PromptContext(
    system_prompt="You are helpful",
    user_prompt="What is AI?"
)

# Add context blocks
ctx.add_context("Machine learning is...")
ctx.add_context("Deep learning uses neural networks...")

# Get merged prompt
merged = ctx.merge_contexts()

# Recalculate tokens after changes
ctx.recalculate_tokens()
print(ctx.total_tokens_estimated)
```

## Wheel Distribution

### Building Wheels

Wheels are platform-specific binary distributions:

```bash
maturin build --release
ls -lh dist/
# Output: vibeforge_prompt-0.1.0-cp310-cp310-linux_x86_64.whl (or similar)
```

Wheel naming convention:

- `vibeforge_prompt`: Package name
- `0.1.0`: Version
- `cp310`: CPython 3.10
- `linux_x86_64`: Platform

### Distributing Wheels

Place wheels in `dist/` for distribution or upload to PyPI:

```bash
pip install twine
twine upload dist/vibeforge_prompt-*.whl
```

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'vibeforge_prompt'"

**Cause:** Extension not built
**Solution:** Run `maturin develop`

### Error: "ImportError: libc.so.6: cannot open shared object"

**Cause:** Rust dependencies not linked
**Solution:** Ensure Rust stable is installed: `rustup default stable`

### Error: "Cannot find Cargo.toml"

**Cause:** Wrong working directory or missing manifest-path
**Solution:** Run from project root and verify pyproject.toml has correct `manifest-path`

### Slow Compilation (First Time)

First build downloads dependencies (~2-3 min). Subsequent builds are faster. Use `maturin develop --release` for release optimizations.

### Python Version Mismatch

Rust extension must match your Python version. Check:

```bash
python3 --version
python3 -m maturin --version
```

Ensure `requires-python = ">=3.10"` matches your environment.

## Development Workflow

### Making Changes to Rust Code

```bash
# 1. Edit rust/forge_prompt/src/lib.rs
# 2. Rebuild
maturin develop

# 3. Test immediately (Python hot-reloads the extension)
python3 -c "from vibeforge_prompt import ..."
```

### Making Changes to Python Code

No rebuild needed - Python changes take effect immediately:

```bash
# Edit python/app/routers/vibeforge.py
# FastAPI reload picks up changes automatically
```

### Full Clean Rebuild

```bash
rm -rf rust/target
maturin develop --release
```

## Platform-Specific Notes

### Linux

- Uses GCC or Clang
- Produces `.so` files
- Requires: `build-essential`, `libssl-dev` (usually pre-installed)

### macOS

- Uses Clang
- Produces `.dylib` files
- May require Xcode Command Line Tools: `xcode-select --install`

### Windows

- Uses MSVC or MinGW
- Produces `.pyd` files
- Requires Visual Studio Build Tools or MinGW

## Integration with FastAPI

Example router using the extension:

```python
from fastapi import APIRouter
from vibeforge_prompt import build_prompt, estimate_tokens_for_prompt

router = APIRouter(prefix="/v1/vibeforge", tags=["VibeForge"])

@router.post("/run")
async def create_run(request: CreateRunRequest):
    # Build prompt using Rust extension
    final_prompt = build_prompt(
        contexts=request.context_ids,
        prompt=request.prompt
    )

    # Estimate tokens
    estimated_tokens = estimate_tokens_for_prompt(
        contexts=request.context_ids,
        prompt=request.prompt
    )

    # ... rest of handler
```

## Performance Characteristics

- **estimate_tokens()**: ~1-10 microseconds (very fast)
- **estimate_tokens_precise()**: ~10-50 microseconds (still very fast)
- **build_prompt()**: Linear in total context length
- **PromptContext**: O(1) operations per add, O(n) for merge/recalculate

## Next Steps

1. **Integrate with FastAPI routers**: Use `build_prompt()` in your endpoints
2. **Add LLM provider integration**: Call external APIs with built prompts
3. **Extend Rust crate**: Add more performance-critical functions
4. **Add tests**: Create pytest tests in `tests/` directory
5. **Deploy**: Build wheels for your target platforms and distribute

---

For more information:

- [Maturin Documentation](https://www.maturin.rs/)
- [PyO3 Guide](https://pyo3.rs/)
- [Rust Book](https://doc.rust-lang.org/book/)
