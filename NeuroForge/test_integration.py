#!/usr/bin/env python3
"""
Quick integration test for Multi-AI Planning System.

Tests the wiring between NeuroForge and DataForge components.
"""

import asyncio
import sys
from pathlib import Path

# Add NeuroForge backend to path
sys.path.insert(0, str(Path(__file__).parent / "neuroforge_backend"))


async def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")

    try:
        from clients.dataforge_client import DataForgeClient, create_dataforge_client
        print("✓ DataForge client imports")
    except Exception as e:
        print(f"✗ DataForge client import failed: {e}")
        return False

    try:
        from services.multi_ai_executor import MultiAIExecutor, StageResult, PlanningResult
        print("✓ MultiAI executor imports")
    except Exception as e:
        print(f"✗ MultiAI executor import failed: {e}")
        return False

    try:
        from routers.orchestration import router, get_executor
        print("✓ Orchestration router imports")
    except Exception as e:
        print(f"✗ Orchestration router import failed: {e}")
        return False

    return True


async def test_dataforge_client():
    """Test DataForge client initialization."""
    print("\nTesting DataForge client...")

    from clients.dataforge_client import create_dataforge_client

    try:
        # Create client (won't connect yet)
        client = create_dataforge_client(
            base_url="http://localhost:8001",
            api_key=None
        )
        print(f"✓ DataForge client created: {client.base_url}")

        # Try health check (will fail if DataForge not running, but that's OK for this test)
        try:
            healthy = await client.health_check()
            if healthy:
                print("✓ DataForge is running and healthy")
            else:
                print("⚠ DataForge health check returned False (may not be running)")
        except Exception as e:
            print(f"⚠ DataForge health check failed (may not be running): {e}")

        # Close client
        await client.close()
        print("✓ DataForge client closed cleanly")

        return True
    except Exception as e:
        print(f"✗ DataForge client test failed: {e}")
        return False


async def test_executor_initialization():
    """Test MultiAI executor initialization with mock router."""
    print("\nTesting executor initialization...")

    from services.multi_ai_executor import MultiAIExecutor
    from clients.dataforge_client import create_dataforge_client

    try:
        # Create mock model router
        class MockModelRouter:
            async def execute(self, model, provider, prompt, temperature, max_tokens):
                return {
                    "output": f"Mock response from {model}",
                    "tokens_in": 100,
                    "tokens_out": 200
                }

        # Create DataForge client
        dataforge_client = create_dataforge_client()

        # Create executor
        executor = MultiAIExecutor(
            model_router=MockModelRouter(),
            dataforge_client=dataforge_client
        )

        print("✓ Executor initialized with mock router and DataForge client")
        print(f"  - Default models configured: {list(executor.default_models.keys())}")
        print(f"  - DataForge client present: {executor.dataforge_client is not None}")

        # Close client
        await dataforge_client.close()

        return True
    except Exception as e:
        print(f"✗ Executor initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all integration tests."""
    print("=" * 70)
    print("Multi-AI Planning System Integration Test")
    print("=" * 70)

    tests = [
        ("Imports", test_imports),
        ("DataForge Client", test_dataforge_client),
        ("Executor Initialization", test_executor_initialization),
    ]

    results = []
    for test_name, test_func in tests:
        result = await test_func()
        results.append((test_name, result))

    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in results)

    print("\n" + ("=" * 70))
    if all_passed:
        print("✅ All integration tests passed!")
        print("\nNext steps:")
        print("1. Start DataForge: cd DataForge && python -m uvicorn app.main:app --port 8001")
        print("2. Start NeuroForge: cd NeuroForge/neuroforge_backend && python main.py")
        print("3. Test planning endpoint: POST http://localhost:8000/api/v1/orchestrate/planning")
        return 0
    else:
        print("❌ Some integration tests failed!")
        print("\nCheck error messages above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
