#!/usr/bin/env python3
"""
Demonstration and testing of the vibeforge_prompt Rust extension module.

This script shows how to use the compiled Rust extension functions:
- build_prompt: Combine contexts and user prompt
- estimate_tokens: Quick token estimation (naive method)
- estimate_tokens_precise: More accurate token estimation
- build_initial_run: Create initial run JSON record
- PromptContext: Stateful context management class
"""

import json
import sys
from pathlib import Path

def main():
    print("\n" + "="*70)
    print("VibeForge Rust Extension Module Demo")
    print("="*70)
    
    # Import the compiled extension module
    try:
        from vibeforge_prompt import (
            build_prompt,
            estimate_tokens,
            estimate_tokens_precise,
            build_initial_run,
            estimate_tokens_for_prompt,
            PromptContext,
        )
        print("\n✓ Successfully imported vibeforge_prompt extension module")
        print("\nAvailable functions and classes:")
        print("  • build_prompt(contexts: List[str], prompt: str) -> str")
        print("  • estimate_tokens(text: str) -> int")
        print("  • estimate_tokens_precise(text: str) -> int")
        print("  • build_initial_run(model: str, prompt: str) -> str (JSON)")
        print("  • estimate_tokens_for_prompt(contexts: List[str], prompt: str) -> int")
        print("  • PromptContext(system_prompt: str, user_prompt: str)")
        
    except ImportError as e:
        print(f"\n✗ Failed to import vibeforge_prompt: {e}")
        print("\nMake sure you've built the extension with:")
        print("  ./build_rust.sh develop")
        print("or")
        print("  maturin develop")
        sys.exit(1)
    
    print("\n" + "-"*70)
    print("DEMONSTRATION 1: Token Estimation")
    print("-"*70)
    
    sample_text = """
    The VibeForge backend is a high-performance prompt engineering system
    that combines FastAPI with Rust extensions for optimal performance.
    It supports token counting, prompt building, and run management.
    """
    
    print(f"\nInput text:\n{sample_text.strip()}\n")
    
    naive_tokens = estimate_tokens(sample_text)
    precise_tokens = estimate_tokens_precise(sample_text)
    
    print(f"Naive token count (~4 chars/token):     {naive_tokens}")
    print(f"Precise token count (word-based):      {precise_tokens}")
    print(f"Character count:                        {len(sample_text.strip())}")
    
    print("\n" + "-"*70)
    print("DEMONSTRATION 2: Building Combined Prompts")
    print("-"*70)
    
    # System context
    system_context = """You are an expert Python and Rust engineer with deep knowledge
of FastAPI, PyO3, and high-performance systems design."""
    
    # Code context
    code_context = """The codebase uses:
- FastAPI for HTTP routing
- Pydantic for data validation
- JSON for MVP persistence (replaceable with Postgres)
- Maturin + PyO3 for Rust-Python integration"""
    
    # User prompt
    user_prompt = "How would you optimize this system for 10k RPS?"
    
    contexts = [system_context, code_context]
    
    print(f"\nSystem Context ({len(system_context)} chars):")
    print(f"  {system_context[:60]}...")
    
    print(f"\nCode Context ({len(code_context)} chars):")
    print(f"  {code_context[:60]}...")
    
    print(f"\nUser Prompt:")
    print(f"  {user_prompt}")
    
    built_prompt = build_prompt(contexts, user_prompt)
    print(f"\nBuilt prompt length: {len(built_prompt)} characters")
    print("\nBuilt prompt structure:")
    print("-" * 40)
    print(built_prompt[:500])
    print("...")
    print("-" * 40)
    
    # Count tokens for the built prompt
    built_tokens = estimate_tokens_for_prompt(contexts, user_prompt)
    print(f"\nTotal token estimation for built prompt: {built_tokens}")
    
    print("\n" + "-"*70)
    print("DEMONSTRATION 3: Creating Run Records")
    print("-"*70)
    
    models = ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]
    prompts = [
        "Explain quantum computing",
        "Write a Python decorator",
        "Design a REST API"
    ]
    
    runs = []
    for model in models:
        for prompt in prompts[:1]:  # Just one prompt per model for demo
            run_json = build_initial_run(model, prompt)
            run_data = json.loads(run_json)
            runs.append(run_data)
            
            print(f"\nModel: {run_data['model']}")
            print(f"  ID:        {run_data['id'][:8]}...")
            print(f"  Status:    {run_data['status']}")
            print(f"  Prompt:    {run_data['prompt'][:50]}...")
            print(f"  Created:   {run_data['created_at']}")
    
    print(f"\n✓ Created {len(runs)} run records")
    
    print("\n" + "-"*70)
    print("DEMONSTRATION 4: PromptContext Class (Stateful)")
    print("-"*70)
    
    # Create a context manager
    system_prompt = "You are a helpful assistant."
    user_prompt = "What is machine learning?"
    
    print(f"\nInitializing PromptContext:")
    print(f"  System: {system_prompt}")
    print(f"  User:   {user_prompt}")
    
    ctx = PromptContext(system_prompt, user_prompt)
    print(f"\nInitial token estimate: {ctx.total_tokens_estimated}")
    
    # Add context blocks
    context_blocks = [
        "Context 1: ML is a subset of AI that enables systems to learn from data",
        "Context 2: Common ML techniques include supervised, unsupervised, and reinforcement learning",
        "Context 3: Popular frameworks: TensorFlow, PyTorch, scikit-learn"
    ]
    
    print(f"\nAdding {len(context_blocks)} context blocks:")
    for i, block in enumerate(context_blocks, 1):
        ctx.add_context(block)
        print(f"  Block {i}: +{estimate_tokens_precise(block)} tokens → Total: {ctx.total_tokens_estimated}")
    
    # Merge contexts
    merged = ctx.merge_contexts()
    print(f"\nMerged context length: {len(merged)} characters")
    print(f"Context blocks in manager: {len(ctx.context_blocks)}")
    
    # Recalculate
    ctx.recalculate_tokens()
    print(f"Recalculated tokens: {ctx.total_tokens_estimated}")
    
    # String representation
    print(f"PromptContext repr: {ctx}")
    
    print("\n" + "-"*70)
    print("DEMONSTRATION 5: Integration Example")
    print("-"*70)
    
    print("\nSimulating an API request workflow:\n")
    
    # Simulated request
    request_contexts = [
        "You are a code review expert",
        "The project uses Python 3.10+ with FastAPI"
    ]
    request_prompt = "Review this API design"
    request_model = "gpt-4"
    
    # Step 1: Build prompt
    print("1. Building combined prompt...")
    final_prompt = build_prompt(request_contexts, request_prompt)
    print(f"   ✓ Prompt built ({len(final_prompt)} chars)")
    
    # Step 2: Estimate tokens
    print("2. Estimating token usage...")
    token_count = estimate_tokens_for_prompt(request_contexts, request_prompt)
    print(f"   ✓ Estimated {token_count} tokens")
    
    # Step 3: Create run record
    print("3. Creating run record...")
    run_json = build_initial_run(request_model, request_prompt)
    run_data = json.loads(run_json)
    print(f"   ✓ Run created: {run_data['id'][:8]}...")
    
    # Step 4: Display summary
    print("\n4. Summary:")
    print(f"   Model:          {request_model}")
    print(f"   Context blocks: {len(request_contexts)}")
    print(f"   Estimated tokens: {token_count}")
    print(f"   Run ID:         {run_data['id']}")
    print(f"   Status:         {run_data['status']}")
    
    print("\n" + "="*70)
    print("Demo Complete!")
    print("="*70)
    print("\nNext Steps:")
    print("1. Integrate build_prompt() in your API routers")
    print("2. Use estimate_tokens() for token budget tracking")
    print("3. Use build_initial_run() to create model run records")
    print("4. Extend PromptContext for advanced context management")
    print("\n")


if __name__ == "__main__":
    main()
