#!/usr/bin/env python3
"""
Test script for VibeForge API implementation.
Run this after starting the development server.

Usage:
    python test_api.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

async def test_llm_service():
    """Test the LLM service with all providers."""
    print("\n" + "=" * 70)
    print("Testing LLM Service")
    print("=" * 70)
    
    from app.services.llm_service import get_llm_service
    
    service = get_llm_service()
    
    # Test token estimation
    print("\n1. Token Estimation")
    print("-" * 70)
    text = "Hello, this is a test prompt for token estimation."
    tokens = service.estimate_tokens("claude", text)
    print(f"Text: {text}")
    print(f"Estimated tokens (Claude): {tokens}")
    
    # Test provider detection
    print("\n2. Provider Detection")
    print("-" * 70)
    test_models = [
        "claude-3-opus-20240229",
        "gpt-4",
        "ollama:mistral",
    ]
    
    for model in test_models:
        provider, parsed_model = service._parse_model_identifier(model)
        print(f"Model: {model:35} → Provider: {provider:10} Model: {parsed_model}")


def test_runs_repository():
    """Test the runs file repository."""
    print("\n" + "=" * 70)
    print("Testing Runs Repository")
    print("=" * 70)
    
    from app.repositories.runs_file import RunsFileRepo
    from pathlib import Path
    import tempfile
    
    # Use temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = RunsFileRepo(data_dir=Path(tmpdir))
        
        # Create run
        print("\n1. Create Run")
        print("-" * 70)
        run = repo.create_run(
            model="gpt-4",
            prompt="Test prompt",
            status="pending",
            active_contexts=[],
        )
        print(f"Created run: {run['id']}")
        print(f"Status: {run['status']}")
        print(f"Created at: {run['created_at']}")
        
        # Get run
        print("\n2. Get Run")
        print("-" * 70)
        retrieved = repo.get_run(run['id'])
        print(f"Retrieved run: {retrieved['id']}")
        print(f"Match: {retrieved['id'] == run['id']}")
        
        # Update run
        print("\n3. Update Run")
        print("-" * 70)
        updated = repo.update_run(
            run['id'],
            output="Test output",
            status="complete",
            tokens_used={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        print(f"Updated run status: {updated['status']}")
        print(f"Output: {updated['output']}")
        print(f"Tokens: {updated['tokens_used']}")
        
        # List runs
        print("\n4. List Runs")
        print("-" * 70)
        history = repo.list_runs(limit=10, offset=0)
        print(f"Total runs: {history['total']}")
        print(f"Items returned: {len(history['items'])}")
        
        # Create more runs for pagination test
        for i in range(5):
            repo.create_run(
                model=f"model-{i}",
                prompt=f"prompt-{i}",
                status="pending",
            )
        
        history = repo.list_runs(limit=3, offset=0)
        print(f"With limit=3: {len(history['items'])} items (offset=0)")
        
        history = repo.list_runs(limit=3, offset=3)
        print(f"With limit=3: {len(history['items'])} items (offset=3)")
        
        # Filter by status
        print("\n5. Filter By Status")
        print("-" * 70)
        completed = repo.list_runs(status="complete")
        pending = repo.list_runs(status="pending")
        print(f"Completed: {completed['total']}")
        print(f"Pending: {pending['total']}")


def test_pydantic_models():
    """Test Pydantic model validation."""
    print("\n" + "=" * 70)
    print("Testing Pydantic Models")
    print("=" * 70)
    
    from app.models.vibeforge_models import (
        CreateRunRequest,
        ModelRunModel,
        TokenUsageModel,
        ContextBlockModel,
    )
    
    # Test CreateRunRequest
    print("\n1. CreateRunRequest")
    print("-" * 70)
    request = CreateRunRequest(
        model="claude-3-opus-20240229",
        prompt="Explain AI",
        active_contexts=[],
    )
    print(f"✓ Model: {request.model}")
    print(f"✓ Prompt: {request.prompt}")
    print(f"✓ Contexts: {len(request.active_contexts)}")
    
    # Test TokenUsageModel
    print("\n2. TokenUsageModel")
    print("-" * 70)
    tokens = TokenUsageModel(
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
    )
    print(f"✓ Prompt tokens: {tokens.prompt_tokens}")
    print(f"✓ Completion tokens: {tokens.completion_tokens}")
    print(f"✓ Total tokens: {tokens.total_tokens}")
    
    # Test ContextBlockModel
    print("\n3. ContextBlockModel")
    print("-" * 70)
    context = ContextBlockModel(
        id="ctx-001",
        title="Python Guidelines",
        content="Use type hints...",
        kind="code",
        priority=1,
    )
    print(f"✓ ID: {context.id}")
    print(f"✓ Title: {context.title}")
    print(f"✓ Kind: {context.kind}")
    print(f"✓ Priority: {context.priority}")
    
    # Test ModelRunModel
    print("\n4. ModelRunModel")
    print("-" * 70)
    run = ModelRunModel(
        id="run-001",
        model="gpt-4",
        prompt="Test",
        status="complete",
        output="Response",
        tokens_used=tokens,
        created_at="2025-11-18T10:00:00Z",
    )
    print(f"✓ ID: {run.id}")
    print(f"✓ Model: {run.model}")
    print(f"✓ Status: {run.status}")
    print(f"✓ Output: {run.output}")
    print(f"✓ Tokens: {run.tokens_used.total_tokens}")


def test_rust_types():
    """Test Rust PyO3 types."""
    print("\n" + "=" * 70)
    print("Testing Rust Types (PyO3)")
    print("=" * 70)
    
    try:
        from forge_core import TokenUsage, RunStatus, ModelRun
        
        print("\n1. TokenUsage")
        print("-" * 70)
        tokens = TokenUsage(100, 200, 300)
        print(f"✓ Prompt tokens: {tokens.prompt_tokens}")
        print(f"✓ Completion tokens: {tokens.completion_tokens}")
        print(f"✓ Total tokens: {tokens.total_tokens}")
        print(f"✓ Repr: {tokens}")
        
        print("\n2. RunStatus")
        print("-" * 70)
        statuses = [RunStatus.Pending, RunStatus.Running, RunStatus.Complete, RunStatus.Error]
        for status in statuses:
            print(f"✓ Status: {status}")
        
        print("\n3. ModelRun")
        print("-" * 70)
        run = ModelRun(
            id="test-run",
            workspace_id="test-ws",
            model="gpt-4",
            prompt="Test prompt"
        )
        print(f"✓ ID: {run.id}")
        print(f"✓ Model: {run.model}")
        print(f"✓ Prompt: {run.prompt}")
        print(f"✓ Status: {run.status}")
        print(f"✓ Repr: {run}")
        
    except ImportError as e:
        print(f"⚠ Rust modules not available: {e}")
        print("  (This is expected if maturin develop hasn't been run)")


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  VibeForge API Implementation - Test Suite".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        # Test Python components
        test_pydantic_models()
        test_runs_repository()
        await test_llm_service()
        
        # Try Rust components
        test_rust_types()
        
        print("\n" + "=" * 70)
        print("✅ All tests completed!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Start the server: uvicorn app.main:app --reload")
        print("2. Open http://localhost:8000/docs in your browser")
        print("3. Try the endpoints with Swagger UI")
        print()
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
