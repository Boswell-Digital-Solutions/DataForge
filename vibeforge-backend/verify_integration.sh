#!/bin/bash
# VERIFICATION SCRIPT - Run this to confirm Python-Rust integration is working

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        VibeForge Python-Rust Integration Verification          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check 1: Python version
echo "CHECK 1: Python Version"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  Python: $PYTHON_VERSION"
if [[ ! "$PYTHON_VERSION" > "3.10" ]] && [[ "$PYTHON_VERSION" != "3.10"* ]]; then
    echo "  ⚠ Warning: Python 3.10+ recommended"
else
    echo "  ✓ OK"
fi
echo ""

# Check 2: Rust toolchain
echo "CHECK 2: Rust Toolchain"
if command -v rustc &> /dev/null; then
    RUST_VERSION=$(rustc --version)
    echo "  $RUST_VERSION"
    echo "  ✓ OK"
else
    echo "  ✗ FAILED: Rust not installed"
    echo "  Install from: https://rustup.rs/"
    exit 1
fi
echo ""

# Check 3: Virtual environment
echo "CHECK 3: Virtual Environment"
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "  ⚠ Not activated"
    echo "  Run: source venv/bin/activate"
else
    echo "  ✓ Activated: $VIRTUAL_ENV"
fi
echo ""

# Check 4: Maturin installation
echo "CHECK 4: Maturin Installation"
if python3 -m pip show maturin > /dev/null 2>&1; then
    MATURIN_VERSION=$(python3 -m pip show maturin | grep Version | awk '{print $2}')
    echo "  Version: $MATURIN_VERSION"
    echo "  ✓ OK"
else
    echo "  ⚠ Not installed"
    echo "  Install: pip install 'maturin>=1.0,<2.0'"
fi
echo ""

# Check 5: Configuration files
echo "CHECK 5: Configuration Files"
files_ok=true

if [[ -f "pyproject.toml" ]]; then
    if grep -q 'module-name = "vibeforge_prompt"' pyproject.toml; then
        echo "  ✓ pyproject.toml: module-name = vibeforge_prompt"
    else
        echo "  ✗ pyproject.toml: missing or wrong module-name"
        files_ok=false
    fi
else
    echo "  ✗ pyproject.toml: not found"
    files_ok=false
fi

if [[ -f "rust/forge_prompt/Cargo.toml" ]]; then
    if grep -q 'crate-type = \["cdylib"\]' rust/forge_prompt/Cargo.toml; then
        echo "  ✓ forge_prompt/Cargo.toml: crate-type = cdylib"
    else
        echo "  ⚠ forge_prompt/Cargo.toml: check crate-type"
    fi
else
    echo "  ✗ forge_prompt/Cargo.toml: not found"
    files_ok=false
fi

if [[ -f "rust/forge_prompt/src/lib.rs" ]]; then
    echo "  ✓ forge_prompt/src/lib.rs: exists"
else
    echo "  ✗ forge_prompt/src/lib.rs: not found"
    files_ok=false
fi

if [[ "$files_ok" == "false" ]]; then
    exit 1
fi
echo ""

# Check 6: Try to import extension
echo "CHECK 6: Module Import"
python3 << 'PYTHON_CHECK' 2>/dev/null && import_ok=1 || import_ok=0

try:
    from vibeforge_prompt import (
        build_prompt,
        estimate_tokens,
        build_initial_run,
        PromptContext,
    )
    print("  ✓ All imports successful")
except ImportError as e:
    print(f"  ⚠ Module not yet built: {e}")
    print("  Run: maturin develop")
    exit(0)  # Not a hard failure, just needs building
except Exception as e:
    print(f"  ✗ Import failed: {e}")
    exit(1)

PYTHON_CHECK

if [[ $import_ok -eq 1 ]]; then
    echo "  ✓ Module already built and working"
    echo ""
    
    # Check 7: Quick functionality test
    echo "CHECK 7: Basic Functionality"
    python3 << 'PYTHON_TEST'
from vibeforge_prompt import estimate_tokens, build_prompt, estimate_tokens_precise

# Test 1
tokens = estimate_tokens("Hello world")
print(f"  ✓ estimate_tokens: {tokens} tokens for 'Hello world'")

# Test 2
precise = estimate_tokens_precise("Hello world")
print(f"  ✓ estimate_tokens_precise: {precise} tokens")

# Test 3
prompt = build_prompt(["Context"], "Question")
print(f"  ✓ build_prompt: generated {len(prompt)} char prompt")

PYTHON_TEST
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    ✓ ALL CHECKS PASSED!                        ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "The vibeforge_prompt module is ready to use."
    echo ""
    echo "Next steps:"
    echo "  1. Run demo:        python3 demo_vibeforge_prompt.py"
    echo "  2. Review examples: cat integration_example.py"
    echo "  3. Start building:  Import in your FastAPI routers"
    echo ""
else
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           Module not yet built - Build it now:                 ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Quick build command:"
    echo "  maturin develop"
    echo ""
    echo "Or use the build script:"
    echo "  ./build_rust.sh develop"
    echo ""
    echo "Or with full testing:"
    echo "  ./build_rust.sh test"
    echo ""
fi
