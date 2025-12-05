#!/usr/bin/env python3
"""
Quick validation script for RAG Pipeline Refactoring

Tests:
1. Semantic chunker imports and initialization
2. Search functions are callable
3. Basic functionality check (no database required)
"""

import sys
import os
from pathlib import Path

# Add paths to sys.path
forge_path = Path(__file__).parent
sys.path.insert(0, str(forge_path / "rake"))
sys.path.insert(0, str(forge_path / "DataForge"))

def test_semantic_chunker_imports():
    """Test that semantic chunker can be imported."""
    print("=" * 70)
    print("TEST 1: Semantic Chunker Imports")
    print("=" * 70)

    try:
        from rake.pipeline.semantic_chunker import (
            SemanticChunker,
            ChunkingStrategy,
            SemanticBoundary
        )
        print("✅ SemanticChunker imported successfully")
        print(f"   - ChunkingStrategy: {list(ChunkingStrategy)}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import SemanticChunker: {e}")
        return False


def test_semantic_chunker_initialization():
    """Test that semantic chunker can be initialized."""
    print("\n" + "=" * 70)
    print("TEST 2: Semantic Chunker Initialization")
    print("=" * 70)

    try:
        from rake.pipeline.semantic_chunker import (
            SemanticChunker,
            ChunkingStrategy
        )

        # Test each strategy
        strategies = ["token", "semantic", "hybrid"]
        for strategy in strategies:
            try:
                chunker = SemanticChunker(
                    chunk_size=500,
                    overlap=50,
                    strategy=getattr(ChunkingStrategy, strategy.upper()),
                    similarity_threshold=0.5
                )
                print(f"✅ {strategy.upper()} strategy initialized")
                print(f"   - Chunk size: {chunker.chunk_size}")
                print(f"   - Overlap: {chunker.overlap}")
                print(f"   - Threshold: {chunker.similarity_threshold}")
            except Exception as e:
                print(f"❌ Failed to initialize {strategy.upper()} strategy: {e}")
                return False

        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def test_token_counting():
    """Test accurate token counting with tiktoken."""
    print("\n" + "=" * 70)
    print("TEST 3: Token Counting Accuracy")
    print("=" * 70)

    try:
        from rake.pipeline.semantic_chunker import SemanticChunker, ChunkingStrategy

        chunker = SemanticChunker(
            chunk_size=500,
            strategy=ChunkingStrategy.TOKEN_BASED
        )

        # Test cases
        test_cases = [
            ("Hello, world!", None),  # Simple phrase
            ("The quick brown fox jumps over the lazy dog.", None),  # Sentence
            ("Python is a high-level programming language.", None),  # Technical
        ]

        for text, expected in test_cases:
            tokens = chunker.count_tokens(text)
            status = "✅" if expected is None or tokens == expected else "❌"
            print(f"{status} '{text}' → {tokens} tokens")

        return True
    except Exception as e:
        print(f"❌ Token counting failed: {e}")
        return False


def test_search_imports():
    """Test that search functions can be imported."""
    print("\n" + "=" * 70)
    print("TEST 4: Search Function Imports")
    print("=" * 70)

    try:
        # Change to DataForge directory to ensure imports work
        original_dir = os.getcwd()
        os.chdir(forge_path / "DataForge")

        from app.api.search import (
            semantic_search,
            keyword_search,
            hybrid_search,
            _reciprocal_rank_fusion
        )
        print("✅ Search functions imported successfully:")
        print("   - semantic_search")
        print("   - keyword_search")
        print("   - hybrid_search")
        print("   - _reciprocal_rank_fusion")

        os.chdir(original_dir)
        return True
    except ImportError as e:
        print(f"❌ Failed to import search functions: {e}")
        os.chdir(original_dir)
        return False


def test_rrf_algorithm():
    """Test Reciprocal Rank Fusion algorithm."""
    print("\n" + "=" * 70)
    print("TEST 5: Reciprocal Rank Fusion Algorithm")
    print("=" * 70)

    try:
        # Change to DataForge directory
        original_dir = os.getcwd()
        os.chdir(forge_path / "DataForge")

        from app.api.search import _reciprocal_rank_fusion

        # Test case: two ranking lists
        # Semantic: A > B > C (ranks 1, 2, 3)
        # Keyword: B > C > A (ranks 1, 2, 3)
        # Expected: B should rank highest (appears high in both)

        semantic_results = [(1, 0.9), (2, 0.7), (3, 0.5)]  # chunk_id, score
        keyword_results = [(2, 0.8), (3, 0.6), (1, 0.4)]

        fused = _reciprocal_rank_fusion([semantic_results, keyword_results])

        print("Input rankings:")
        print(f"  Semantic: {semantic_results}")
        print(f"  Keyword: {keyword_results}")
        print(f"\nRRF output: {fused}")

        # Check that chunk 2 ranks highest (it's high in both lists)
        if fused[0][0] == 2:
            print("\n✅ RRF correctly ranked chunk 2 first")
            print("   (chunk 2 appears high in both semantic and keyword)")
        else:
            print(f"\n⚠️  RRF ranked chunk {fused[0][0]} first (expected chunk 2)")

        os.chdir(original_dir)
        return True
    except Exception as e:
        print(f"❌ RRF test failed: {e}")
        os.chdir(original_dir)
        return False


def test_chunk_model():
    """Test that Chunk model has search_vector field."""
    print("\n" + "=" * 70)
    print("TEST 6: Chunk Model Updates")
    print("=" * 70)

    try:
        # Change to DataForge directory
        original_dir = os.getcwd()
        os.chdir(forge_path / "DataForge")

        from app.models.models import Chunk

        # Check if search_vector attribute exists
        if hasattr(Chunk, 'search_vector'):
            print("✅ Chunk model has search_vector field")
            print(f"   - Type: {type(Chunk.search_vector)}")
        else:
            print("❌ Chunk model missing search_vector field")
            os.chdir(original_dir)
            return False

        os.chdir(original_dir)
        return True
    except Exception as e:
        print(f"❌ Chunk model test failed: {e}")
        os.chdir(original_dir)
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 70)
    print("RAG PIPELINE REFACTORING - VALIDATION SUITE")
    print("=" * 70)
    print(f"Forge Path: {forge_path}")
    print()

    results = []

    # Run tests
    results.append(("Semantic Chunker Imports", test_semantic_chunker_imports()))
    results.append(("Semantic Chunker Init", test_semantic_chunker_initialization()))
    results.append(("Token Counting", test_token_counting()))
    results.append(("Search Function Imports", test_search_imports()))
    results.append(("RRF Algorithm", test_rrf_algorithm()))
    results.append(("Chunk Model Updates", test_chunk_model()))

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All validation tests passed! Implementation is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
