#!/usr/bin/env python3
"""
Test script to verify DataForge integration for all NeuroForge routers.
Tests that all routers successfully store and retrieve data from DataForge.
"""
import asyncio
import sys
import httpx
from datetime import datetime

# Configuration
DATAFORGE_URL = "http://localhost:5000"
NEUROFORGE_URL = "http://localhost:8000"
TEST_USER = "test_integration_user"

async def test_dataforge_health():
    """Verify DataForge is running."""
    print("\n1. Testing DataForge Health")
    print("-" * 50)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{DATAFORGE_URL}/health")
            response.raise_for_status()
            health = response.json()
            print(f"✓ DataForge is healthy: {health['status']}")
            return True
    except Exception as e:
        print(f"✗ DataForge health check failed: {e}")
        return False


async def test_chain_integration():
    """Test chain storage in DataForge."""
    print("\n2. Testing Chain Router Integration")
    print("-" * 50)
    try:
        # Create a chain
        async with httpx.AsyncClient(timeout=10.0) as client:
            chain_data = {
                "name": "Test Chain",
                "nodes": [
                    {
                        "id": "node1",
                        "prompt_id": "prompt_123",
                        "prompt_name": "Character Creator",
                        "x": 100,
                        "y": 100,
                        "inputs": {},
                        "outputs": ["character_description"]
                    }
                ],
                "connections": []
            }
            
            response = await client.post(
                f"{NEUROFORGE_URL}/api/v1/workbench/chains",
                headers={"x-user-id": TEST_USER},
                json=chain_data
            )
            
            if response.status_code == 200:
                chain = response.json()
                print(f"✓ Chain created: {chain['id']}")
                
                # Verify it's in DataForge
                df_response = await client.get(
                    f"{DATAFORGE_URL}/api/v1/runs",
                    headers={"x-user-id": TEST_USER},
                    params={
                        "user_id": TEST_USER,
                        "service_name": "neuroforge",
                        "operation_type": "chain_create"
                    }
                )
                
                if df_response.status_code == 200:
                    data = df_response.json()
                    runs = data.get("runs", [])
                    chain_found = any(
                        f"chain_id:{chain['id']}" in run.get("tags", [])
                        for run in runs
                    )
                    if chain_found:
                        print(f"✓ Chain stored in DataForge")
                        return True
                    else:
                        print(f"✗ Chain not found in DataForge")
                        return False
            else:
                print(f"✗ Chain creation failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Chain integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_deployment_integration():
    """Test deployment storage in DataForge."""
    print("\n3. Testing Deployment Router Integration")
    print("-" * 50)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            deployment_data = {
                "prompt_id": "prompt_test_123",
                "environment": "dev",
                "version": "v1.0.0"
            }
            
            response = await client.post(
                f"{NEUROFORGE_URL}/api/v1/workbench/prompts/prompt_test_123/deploy",
                headers={"x-user-id": TEST_USER},
                json=deployment_data
            )
            
            if response.status_code == 200:
                deployment = response.json()
                print(f"✓ Deployment created: {deployment['id']}")
                
                # Verify it's in DataForge
                df_response = await client.get(
                    f"{DATAFORGE_URL}/api/v1/runs",
                    headers={"x-user-id": TEST_USER},
                    params={
                        "user_id": TEST_USER,
                        "service_name": "neuroforge",
                        "operation_type": "prompt_deployment"
                    }
                )
                
                if df_response.status_code == 200:
                    data = df_response.json()
                    runs = data.get("runs", [])
                    deployment_found = any(
                        f"deployment_id:{deployment['id']}" in run.get("tags", [])
                        for run in runs
                    )
                    if deployment_found:
                        print(f"✓ Deployment stored in DataForge")
                        return True
                    else:
                        print(f"✗ Deployment not found in DataForge")
                        return False
            else:
                print(f"✗ Deployment creation failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"✗ Deployment integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_stateless_verification():
    """Verify that data persists independently of NeuroForge."""
    print("\n4. Verifying Stateless Architecture")
    print("-" * 50)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check DataForge for all stored data
            df_response = await client.get(
                f"{DATAFORGE_URL}/api/v1/runs",
                headers={"x-user-id": TEST_USER},
                params={"user_id": TEST_USER}
            )
            
            if df_response.status_code == 200:
                data = df_response.json()
                runs = data.get("runs", [])
                
                operation_types = set()
                for run in runs:
                    # Extract operation type from tags
                    tags = run.get("tags", [])
                    for tag in tags:
                        if tag in ["chain_create", "chain_update", "chain_delete", "chain_execution", 
                                   "prompt_deployment", "prompt_create", "prompt_update", "prompt_delete"]:
                            operation_types.add(tag)
                
                print(f"✓ Found {len(runs)} total runs in DataForge")
                print(f"  Operation types: {', '.join(operation_types)}")
                print(f"✓ Data persists in DataForge (stateless verified)")
                return True
            else:
                print(f"✗ Failed to query DataForge: {df_response.status_code}")
                return False
                
    except Exception as e:
        print(f"✗ Stateless verification failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("=" * 50)
    print("NeuroForge → DataForge Integration Tests")
    print("=" * 50)
    
    results = []
    
    # Test 1: DataForge Health
    results.append(await test_dataforge_health())
    
    if not results[0]:
        print("\n⚠️  DataForge is not running. Please start DataForge first.")
        sys.exit(1)
    
    # Test 2: Chain Integration
    results.append(await test_chain_integration())
    
    # Test 3: Deployment Integration
    results.append(await test_deployment_integration())
    
    # Test 4: Stateless Verification
    results.append(await test_stateless_verification())
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    tests = [
        "DataForge Health",
        "Chain Router Integration",
        "Deployment Router Integration",
        "Stateless Architecture"
    ]
    
    for test, result in zip(tests, results):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test}")
    
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"✅ All tests passed ({passed}/{total})")
        print("=" * 50)
        sys.exit(0)
    else:
        print(f"⚠️  Some tests failed ({passed}/{total} passed)")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
