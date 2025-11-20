#!/bin/bash
# Build script for VibeForge Rust -> Python integration using Maturin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}VibeForge Rust Extension Builder${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if Python venv is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    if [[ ! -d "venv" ]]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
fi

# Check for Rust
if ! command -v rustc &> /dev/null; then
    echo "Rust is not installed. Please install from https://rustup.rs/"
    exit 1
fi

# Check for Maturin
if ! python -m pip show maturin > /dev/null 2>&1; then
    echo -e "${BLUE}Installing maturin...${NC}"
    pip install 'maturin>=1.0,<2.0'
fi

if [[ "$1" == "develop" ]] || [[ -z "$1" ]]; then
    echo -e "${GREEN}Building extension module (development mode)...${NC}"
    maturin develop
    echo -e "${GREEN}✓ Development build complete!${NC}"
    echo ""
    echo "The vibeforge_prompt module is now installed in your Python environment."
    echo "You can import it with: from vibeforge_prompt import build_prompt, estimate_tokens, build_initial_run"
    
elif [[ "$1" == "release" ]]; then
    echo -e "${GREEN}Building extension module (release mode)...${NC}"
    maturin develop --release
    echo -e "${GREEN}✓ Release build complete!${NC}"
    
elif [[ "$1" == "build" ]]; then
    echo -e "${GREEN}Building wheel...${NC}"
    maturin build
    echo -e "${GREEN}✓ Wheel build complete!${NC}"
    echo ""
    echo "Wheels are located in: dist/"
    
elif [[ "$1" == "clean" ]]; then
    echo -e "${BLUE}Cleaning build artifacts...${NC}"
    rm -rf rust/target
    rm -rf dist
    rm -rf build
    echo -e "${GREEN}✓ Clean complete!${NC}"
    
elif [[ "$1" == "test" ]]; then
    echo -e "${BLUE}Testing Rust extension...${NC}"
    maturin develop
    python3 << 'PYTEST'
import sys
print("\n" + "="*50)
print("Testing vibeforge_prompt module")
print("="*50 + "\n")

try:
    from vibeforge_prompt import (
        build_prompt,
        estimate_tokens,
        estimate_tokens_precise,
        build_initial_run,
        estimate_tokens_for_prompt,
        PromptContext
    )
    print("✓ All imports successful\n")
    
    # Test 1: estimate_tokens
    print("Test 1: estimate_tokens()")
    text = "This is a test prompt with some content."
    tokens = estimate_tokens(text)
    print(f"  Input: '{text}'")
    print(f"  Tokens (naive): {tokens}")
    assert tokens > 0, "Token count should be positive"
    print("  ✓ PASSED\n")
    
    # Test 2: estimate_tokens_precise
    print("Test 2: estimate_tokens_precise()")
    tokens_precise = estimate_tokens_precise(text)
    print(f"  Input: '{text}'")
    print(f"  Tokens (precise): {tokens_precise}")
    assert tokens_precise > 0, "Token count should be positive"
    print("  ✓ PASSED\n")
    
    # Test 3: build_prompt
    print("Test 3: build_prompt()")
    contexts = ["Context 1: System rules", "Context 2: Code style guidelines"]
    user_prompt = "Implement a function"
    built = build_prompt(contexts, user_prompt)
    print(f"  Contexts: {len(contexts)}")
    print(f"  User prompt: '{user_prompt}'")
    print(f"  Built prompt length: {len(built)} chars")
    assert "Context Information" in built, "Built prompt should contain context marker"
    assert "Task" in built, "Built prompt should contain task marker"
    assert user_prompt in built, "Built prompt should contain user prompt"
    print("  ✓ PASSED\n")
    
    # Test 4: estimate_tokens_for_prompt
    print("Test 4: estimate_tokens_for_prompt()")
    total_tokens = estimate_tokens_for_prompt(contexts, user_prompt)
    print(f"  Total tokens for built prompt: {total_tokens}")
    assert total_tokens > 0, "Token count should be positive"
    print("  ✓ PASSED\n")
    
    # Test 5: build_initial_run
    print("Test 5: build_initial_run()")
    import json
    run_json = build_initial_run("gpt-4", "Test prompt")
    run_data = json.loads(run_json)
    print(f"  Model: {run_data['model']}")
    print(f"  Status: {run_data['status']}")
    print(f"  ID: {run_data['id'][:8]}...")
    assert "id" in run_data, "Run should have ID"
    assert run_data["model"] == "gpt-4", "Model should match"
    assert run_data["status"] == "pending", "Initial status should be pending"
    print("  ✓ PASSED\n")
    
    # Test 6: PromptContext class
    print("Test 6: PromptContext class")
    ctx = PromptContext("System prompt here", "User prompt here")
    print(f"  System prompt tokens: {ctx.total_tokens_estimated}")
    ctx.add_context("Additional context")
    print(f"  After adding context: {ctx.total_tokens_estimated}")
    merged = ctx.merge_contexts()
    print(f"  Merged contexts length: {len(merged)} chars")
    ctx.recalculate_tokens()
    print(f"  Recalculated tokens: {ctx.total_tokens_estimated}")
    print("  ✓ PASSED\n")
    
    print("="*50)
    print("All tests passed! ✓")
    print("="*50)
    
except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("\nMake sure the extension was built successfully with: maturin develop")
    sys.exit(1)
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTEST
    echo -e "${GREEN}✓ Tests complete!${NC}"
    
else
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  develop (default)  Build and install extension in development mode"
    echo "  release            Build and install extension in release mode"
    echo "  build              Build wheel distribution"
    echo "  clean              Clean all build artifacts"
    echo "  test               Build and run tests"
    echo ""
    exit 1
fi
