"""
Example demonstrating telemetry integration in NeuroForge.

This shows how to emit telemetry events for LLM requests.
"""

import sys
import os
import time
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge_telemetry import TelemetryClient

# NeuroForge uses same database as DataForge for shared telemetry
# Point to DataForge's database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////home/charles/projects/Coding2025/Forge/DataForge/dataforge.db"
)


# Model pricing (example - update with real pricing)
MODEL_PRICING = {
    "gpt-4": 0.03 / 1000,  # $0.03 per 1K tokens
    "gpt-3.5-turbo": 0.002 / 1000,  # $0.002 per 1K tokens
    "claude-3-opus": 0.015 / 1000,
    "claude-3-sonnet": 0.003 / 1000,
}


def example_llm_request_with_telemetry(prompt: str, model: str):
    """
    Example function showing how to add telemetry to an LLM request.

    This demonstrates the pattern to use in real NeuroForge endpoints.
    """
    telemetry = TelemetryClient(DATABASE_URL)
    correlation_id = uuid.uuid4()
    start_time = time.time()

    print(f"\n🤖 Sending prompt to {model}")
    print(f"📊 Correlation ID: {correlation_id}")
    print(f"💬 Prompt: '{prompt[:50]}...'")

    try:
        # Simulate LLM request
        time.sleep(0.3)  # Simulate API latency

        # Simulate response
        response = {
            "text": "This is a simulated response from the LLM.",
            "prompt_tokens": 25,
            "completion_tokens": 50,
            "total_tokens": 75,
            "provider": "openai",
        }

        # Calculate metrics
        duration_ms = (time.time() - start_time) * 1000
        cost_usd = response["total_tokens"] * MODEL_PRICING.get(model, 0.001)

        # Emit SUCCESS event
        event_id = telemetry.emit(
            service="neuroforge",
            event_type="model_request",
            severity="info",
            correlation_id=correlation_id,
            metadata={
                "model": model,
                "provider": response["provider"],
                "user": "charles",
                "prompt_preview": prompt[:100],
            },
            metrics={
                "duration_ms": duration_ms,
                "tokens_prompt": response["prompt_tokens"],
                "tokens_completion": response["completion_tokens"],
                "tokens_total": response["total_tokens"],
                "cost_usd": cost_usd,
            }
        )

        print(f"✅ Request completed in {duration_ms:.2f}ms")
        print(f"📤 Telemetry event emitted: {event_id}")
        print(f"💰 Cost: ${cost_usd:.4f} ({response['total_tokens']} tokens)")

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        # Emit ERROR event
        event_id = telemetry.emit(
            service="neuroforge",
            event_type="model_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={
                "model": model,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            metrics={
                "duration_ms": duration_ms,
            }
        )

        print(f"❌ Request failed: {e}")
        print(f"📤 Error telemetry event emitted: {event_id}")

        raise


def example_model_comparison():
    """
    Example showing how to track multiple model requests for comparison.

    All requests use the same correlation_id to link them together.
    """
    telemetry = TelemetryClient(DATABASE_URL)
    correlation_id = uuid.uuid4()

    print(f"\n🔬 Testing multiple models")
    print(f"📊 Shared Correlation ID: {correlation_id}")

    prompt = "Explain quantum computing in simple terms"
    models = ["gpt-3.5-turbo", "gpt-4", "claude-3-sonnet"]

    for model in models:
        start_time = time.time()

        # Simulate request
        time.sleep(0.2)
        tokens = 100 if "gpt-4" in model else 80
        cost = tokens * MODEL_PRICING.get(model, 0.001)

        telemetry.emit(
            service="neuroforge",
            event_type="model_request",
            correlation_id=correlation_id,  # SAME for all!
            metadata={
                "model": model,
                "experiment": "model_comparison",
            },
            metrics={
                "duration_ms": (time.time() - start_time) * 1000,
                "tokens_total": tokens,
                "cost_usd": cost,
            }
        )

        print(f"  ✅ {model}: {tokens} tokens, ${cost:.4f}")

    print("\n💡 All events share correlation_id - can compare in dashboard!")


if __name__ == "__main__":
    print("=" * 60)
    print("NeuroForge Telemetry Example")
    print("=" * 60)

    # Example 1: Single LLM request
    example_llm_request_with_telemetry(
        prompt="What is machine learning?",
        model="gpt-3.5-turbo"
    )

    # Example 2: Model comparison
    example_model_comparison()

    print("\n" + "=" * 60)
    print("✨ Telemetry examples completed successfully!")
    print("=" * 60)
    print("\nTo view NeuroForge events:")
    print("  SELECT * FROM events WHERE service = 'neuroforge' ORDER BY timestamp DESC;")
    print("\nTo see model cost comparison:")
    print("  SELECT model, AVG(json_extract(metrics, '$.cost_usd')) as avg_cost")
    print("  FROM events")
    print("  WHERE service = 'neuroforge'")
    print("  GROUP BY model;")
