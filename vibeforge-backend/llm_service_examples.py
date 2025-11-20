"""
Example usage of the Unified LLM Service.

Demonstrates:
- Calling different LLM providers
- Token estimation
- Error handling
- Custom model registration
"""

import asyncio
import json
from typing import List

# Import the LLM service
from app.services.llm_service import (
    get_llm_service,
    call_llm,
    estimate_tokens,
    LLMResponse,
)


# ============================================================================
# EXAMPLE 1: Basic LLM Calls
# ============================================================================

async def example_basic_calls():
    """Basic examples of calling different LLM providers."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic LLM Calls")
    print("="*70)
    
    service = get_llm_service()
    
    # Example 1a: Call GPT-4
    print("\n[1a] Calling GPT-4...")
    try:
        response = await call_llm("gpt-4", "What is machine learning?")
        print(f"  Model: {response.model}")
        print(f"  Provider: {response.provider}")
        print(f"  Content: {response.content[:100]}...")
        print(f"  Tokens: {response.prompt_tokens} → {response.completion_tokens}")
        print(f"  Latency: {response.latency_ms:.0f}ms")
    except Exception as e:
        print(f"  Note: {e}")
    
    # Example 1b: Call Claude
    print("\n[1b] Calling Claude...")
    try:
        response = await call_llm("claude-3-opus", "Explain AI in one sentence")
        print(f"  Model: {response.model}")
        print(f"  Content: {response.content[:100]}...")
        print(f"  Tokens: {response.total_tokens}")
    except Exception as e:
        print(f"  Note: {e}")
    
    # Example 1c: Call local Ollama
    print("\n[1c] Calling local Ollama (if available)...")
    try:
        response = await call_llm("local-mistral", "Say hello")
        print(f"  Model: {response.model}")
        print(f"  Content: {response.content[:100]}...")
    except Exception as e:
        print(f"  Note: {e} (Ollama may not be running)")


# ============================================================================
# EXAMPLE 2: Token Estimation
# ============================================================================

def example_token_estimation():
    """Examples of token estimation across providers."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Token Estimation")
    print("="*70)
    
    texts = [
        "The quick brown fox",
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data without being explicitly programmed.",
        "What is the meaning of life, the universe, and everything?" * 5,
    ]
    
    for text in texts:
        print(f"\nText: '{text[:50]}...' ({len(text)} chars)")
        
        tokens_gpt = estimate_tokens("gpt-4", text)
        tokens_claude = estimate_tokens("claude-3-opus", text)
        tokens_ollama = estimate_tokens("local-mistral", text)
        
        print(f"  GPT-4:    {tokens_gpt} tokens")
        print(f"  Claude:   {tokens_claude} tokens")
        print(f"  Ollama:   {tokens_ollama} tokens")


# ============================================================================
# EXAMPLE 3: Batch Processing
# ============================================================================

async def example_batch_processing():
    """Process multiple prompts efficiently."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Batch Processing")
    print("="*70)
    
    prompts = [
        "What is AI?",
        "Explain machine learning",
        "What is deep learning?",
    ]
    
    print(f"\nProcessing {len(prompts)} prompts with GPT-4...")
    
    try:
        tasks = [
            call_llm("gpt-4", prompt, max_tokens=100)
            for prompt in prompts
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_tokens = 0
        for i, (prompt, response) in enumerate(zip(prompts, responses)):
            if isinstance(response, LLMResponse):
                print(f"\n  [{i+1}] {prompt}")
                print(f"      Response: {response.content[:60]}...")
                print(f"      Tokens: {response.total_tokens}")
                total_tokens += response.total_tokens
            else:
                print(f"\n  [{i+1}] {prompt}")
                print(f"      Error: {response}")
        
        print(f"\nTotal tokens: {total_tokens}")
    except Exception as e:
        print(f"Batch processing error: {e}")


# ============================================================================
# EXAMPLE 4: Model-Specific Configuration
# ============================================================================

async def example_model_configuration():
    """Configure models with custom parameters."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Model-Specific Configuration")
    print("="*70)
    
    service = get_llm_service()
    
    # Override max_tokens for a specific model
    print("\nCalling with custom max_tokens=50...")
    try:
        response = await service.call_llm(
            model="gpt-4",
            prompt="Tell me a long story",
            max_tokens=50  # Limit response length
        )
        print(f"  Completion tokens: {response.completion_tokens}")
        print(f"  Content length: {len(response.content)} chars")
    except Exception as e:
        print(f"  Note: {e}")
    
    # Override timeout for slow models
    print("\nCalling with custom timeout...")
    try:
        response = await service.call_llm(
            model="local-llama",
            prompt="Quick response",
            timeout=60  # 60 second timeout
        )
        print(f"  Success with custom timeout")
    except asyncio.TimeoutError:
        print(f"  Request exceeded timeout")
    except Exception as e:
        print(f"  Note: {e}")


# ============================================================================
# EXAMPLE 5: Provider Status
# ============================================================================

def example_provider_status():
    """Check which providers are available."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Provider Status")
    print("="*70)
    
    service = get_llm_service()
    status = service.get_provider_status()
    
    print("\nProvider availability:")
    for provider, info in status.items():
        available = "✓ Available" if info.get("available") else "✗ Unavailable"
        has_key = "Has API key" if info.get("has_api_key") else "No API key"
        
        print(f"\n  {provider.upper()}")
        print(f"    Status: {available}")
        print(f"    Auth: {has_key}")
        
        if provider == "ollama":
            print(f"    URL: {info.get('base_url')}")


# ============================================================================
# EXAMPLE 6: Integration with FastAPI Router
# ============================================================================

"""
Example FastAPI endpoint using the LLM service:

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_service import call_llm

router = APIRouter()

class LLMRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: int = 2048

class LLMResponseModel(BaseModel):
    content: str
    tokens: int
    provider: str

@router.post("/generate", response_model=LLMResponseModel)
async def generate_text(request: LLMRequest):
    try:
        response = await call_llm(
            model=request.model,
            prompt=request.prompt,
            max_tokens=request.max_tokens
        )
        
        return LLMResponseModel(
            content=response.content,
            tokens=response.total_tokens,
            provider=response.provider,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""


# ============================================================================
# Main Example Runner
# ============================================================================

async def main():
    """Run all examples."""
    print("\n╔════════════════════════════════════════════════════════════════════╗")
    print("║            Unified LLM Service - Usage Examples                     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    
    # Example 1: Basic calls
    await example_basic_calls()
    
    # Example 2: Token estimation
    example_token_estimation()
    
    # Example 3: Batch processing
    await example_batch_processing()
    
    # Example 4: Model configuration
    await example_model_configuration()
    
    # Example 5: Provider status
    example_provider_status()
    
    print("\n" + "="*70)
    print("Examples Complete!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Set environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY)")
    print("  2. Integrate with FastAPI routers")
    print("  3. Add error handling for production")
    print("  4. Monitor token usage and costs")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
