"""
Unified LLM Service for Claude (Anthropic), GPT (OpenAI), and Ollama (Local).

Supports:
- Model detection based on prefix (claude-*, gpt-*, local-*)
- Token estimation via Rust extension (vibeforge_prompt)
- Async/await for non-blocking calls
- Error handling with timeouts
- Structured logging
"""

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, Literal
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Try to import Rust token estimation
try:
    from vibeforge_prompt import estimate_tokens_precise
    RUST_TOKENS_AVAILABLE = True
except ImportError:
    RUST_TOKENS_AVAILABLE = False
    logger.warning("vibeforge_prompt not available, using fallback token estimation")

# Type alias for LLM provider names
LLMProvider = Literal["claude", "openai", "ollama"]


# ============================================================================
# LLM Response and Configuration
# ============================================================================

class LLMResponse:
    """Response from an LLM provider."""

    def __init__(
        self,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str = "",
        provider: str = "",
        latency_ms: float = 0,
    ):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.model = model
        self.provider = provider
        self.latency_ms = latency_ms
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }


class ModelConfig:
    """Configuration for a specific model."""

    def __init__(
        self,
        name: str,
        provider: LLMProvider,
        max_tokens: int = 2048,
        timeout: int = 300,
        temperature: float = 0.7,
    ):
        self.name = name
        self.provider = provider
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.temperature = temperature


# Default model configurations
DEFAULT_MODELS: Dict[str, ModelConfig] = {
    "claude-3-opus": ModelConfig("claude-3-opus-20240229", "claude", max_tokens=4096),
    "claude-3-sonnet": ModelConfig("claude-3-sonnet-20240229", "claude", max_tokens=4096),
    "gpt-4": ModelConfig("gpt-4", "openai", max_tokens=8192),
    "gpt-4-turbo": ModelConfig("gpt-4-turbo-preview", "openai", max_tokens=4096),
    "gpt-3.5-turbo": ModelConfig("gpt-3.5-turbo", "openai", max_tokens=2048),
    "local-mistral": ModelConfig("mistral", "ollama", max_tokens=2048, timeout=600),
    "local-llama": ModelConfig("llama2", "ollama", max_tokens=2048, timeout=600),
}



# ============================================================================
# Abstract Provider Interface
# ============================================================================

class LLMProviderBase(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def send_prompt(self, prompt: str, model: str, max_tokens: int) -> LLMResponse:
        """Send a prompt to the LLM and get a response."""
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        pass



# ============================================================================
# Claude Provider (Anthropic)
# ============================================================================

class ClaudeProvider(LLMProviderBase):
    """Claude provider using Anthropic API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("✓ Claude provider initialized with Anthropic API")
            except ImportError:
                logger.warning("⚠ anthropic package not installed, Claude disabled")
        else:
            logger.warning("⚠ ANTHROPIC_API_KEY not set, Claude disabled")

    async def send_prompt(self, prompt: str, model: str = "claude-3-opus-20240229", max_tokens: int = 2048) -> LLMResponse:
        """Send prompt to Claude."""
        start_time = datetime.now()
        
        if not self.client:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return LLMResponse(
                content="[Claude disabled - API key not configured]",
                prompt_tokens=self.estimate_tokens(prompt),
                completion_tokens=50,
                model=model,
                provider="claude",
                latency_ms=latency,
            )

        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            content = message.content[0].text if message.content else ""
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(f"Claude response: {len(content)} chars, {latency:.0f}ms")
            
            return LLMResponse(
                content=content,
                prompt_tokens=message.usage.input_tokens,
                completion_tokens=message.usage.output_tokens,
                model=model,
                provider="claude",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"✗ Claude API error: {e}")
            raise

    def estimate_tokens(self, text: str) -> int:
        """Estimate Claude tokens using Rust extension or fallback."""
        if RUST_TOKENS_AVAILABLE:
            return estimate_tokens_precise(text)
        return max(1, len(text) // 4)


# ============================================================================
# GPT Provider (OpenAI)
# ============================================================================

class GPTProvider(LLMProviderBase):
    """GPT provider using OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=self.api_key)
                logger.info("✓ GPT provider initialized with OpenAI API")
            except ImportError:
                logger.warning("⚠ openai package not installed, GPT disabled")
        else:
            logger.warning("⚠ OPENAI_API_KEY not set, GPT disabled")

    async def send_prompt(self, prompt: str, model: str = "gpt-4", max_tokens: int = 2048) -> LLMResponse:
        """Send prompt to GPT."""
        start_time = datetime.now()
        
        if not self.client:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return LLMResponse(
                content="[GPT disabled - API key not configured]",
                prompt_tokens=self.estimate_tokens(prompt),
                completion_tokens=50,
                model=model,
                provider="openai",
                latency_ms=latency,
            )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content or ""
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(f"GPT response: {len(content)} chars, {latency:.0f}ms")
            
            return LLMResponse(
                content=content,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                model=model,
                provider="openai",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"✗ OpenAI API error: {e}")
            raise

    def estimate_tokens(self, text: str) -> int:
        """Estimate GPT tokens using Rust extension or fallback."""
        if RUST_TOKENS_AVAILABLE:
            return estimate_tokens_precise(text)
        return max(1, len(text) // 4)


# ============================================================================
# Ollama Provider (Local)
# ============================================================================

class OllamaProvider(LLMProviderBase):
    """Ollama provider for local models."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url
        self.model = model
        self.client = None
        try:
            import requests

            self.client = requests
            logger.info(f"✓ Ollama provider initialized ({model} at {base_url})")
        except ImportError:
            logger.warning("⚠ requests package not installed, Ollama disabled")

    async def send_prompt(self, prompt: str, model: str = "mistral", max_tokens: int = 2048, timeout: int = 300) -> LLMResponse:
        """Send prompt to Ollama."""
        start_time = datetime.now()
        
        if not self.client:
            latency = (datetime.now() - start_time).total_seconds() * 1000
            return LLMResponse(
                content="[Ollama disabled - requests not installed]",
                prompt_tokens=self.estimate_tokens(prompt),
                completion_tokens=50,
                model=model,
                provider="ollama",
                latency_ms=latency,
            )

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.post(
                        f"{self.base_url}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": False},
                        timeout=timeout,
                    ),
                ),
                timeout=timeout + 5,
            )
            
            response.raise_for_status()
            data = response.json()
            content = data.get("response", "")
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(f"Ollama response: {len(content)} chars, {latency:.0f}ms")
            
            # Ollama doesn't return token counts; estimate
            prompt_tokens = self.estimate_tokens(prompt)
            completion_tokens = self.estimate_tokens(content)

            return LLMResponse(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model=model,
                provider="ollama",
                latency_ms=latency,
            )
        except asyncio.TimeoutError:
            logger.error(f"✗ Ollama timeout after {timeout}s")
            raise TimeoutError(f"Ollama request exceeded {timeout}s timeout")
        except Exception as e:
            logger.error(f"✗ Ollama API error: {e}")
            raise

    def estimate_tokens(self, text: str) -> int:
        """Estimate Ollama tokens using Rust extension or fallback."""
        if RUST_TOKENS_AVAILABLE:
            return estimate_tokens_precise(text)
        return max(1, len(text) // 4)



# ============================================================================
# Unified LLM Service
# ============================================================================

class UnifiedLLMService:
    """Unified service for calling any LLM provider."""

    def __init__(self):
        self.providers: Dict[str, LLMProviderBase] = {}
        self.model_configs: Dict[str, ModelConfig] = DEFAULT_MODELS.copy()
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers."""
        self.providers["claude"] = ClaudeProvider()
        self.providers["openai"] = GPTProvider()
        self.providers["ollama"] = OllamaProvider()
        logger.info(f"✓ LLM Service initialized with providers: {list(self.providers.keys())}")

    def _detect_provider(self, model: str) -> Tuple[str, str]:
        """
        Detect provider and model name from model identifier.

        Supports patterns:
        - "claude-3-opus" → ("claude", "claude-3-opus-20240229")
        - "gpt-4" → ("openai", "gpt-4")
        - "gpt-4-turbo" → ("openai", "gpt-4-turbo-preview")
        - "local-mistral" → ("ollama", "mistral")
        - "ollama:llama2" → ("ollama", "llama2")

        Returns:
            (provider_name, model_name)
        """
        # Check for explicit provider specification
        if ":" in model:
            provider_prefix, model_name = model.split(":", 1)
            return provider_prefix.lower(), model_name

        # Check model config first
        if model in self.model_configs:
            config = self.model_configs[model]
            return config.provider, config.name

        # Prefix-based detection
        if model.startswith("claude"):
            return "claude", model
        elif model.startswith("gpt"):
            return "openai", model
        elif model.startswith("local-"):
            return "ollama", model.replace("local-", "")
        else:
            # Default to Ollama for unknown models
            return "ollama", model

    async def call_llm(
        self,
        model: str,
        prompt: str,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> LLMResponse:
        """
        Call an LLM with the given prompt.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-opus", "local-mistral")
            prompt: The prompt to send
            max_tokens: Max tokens for response (uses model default if not specified)
            timeout: Request timeout in seconds (uses provider default if not specified)

        Returns:
            LLMResponse with content, token counts, and latency

        Raises:
            ValueError: If provider not found
            TimeoutError: If request exceeds timeout
            Exception: For other API errors
        """
        provider_name, model_name = self._detect_provider(model)

        if provider_name not in self.providers:
            logger.error(f"✗ Unknown provider: {provider_name}")
            raise ValueError(f"Unknown provider: {provider_name}")

        provider = self.providers[provider_name]
        
        # Get model config for defaults
        config = self.model_configs.get(model)
        if not config:
            config = self.model_configs.get(provider_name, ModelConfig("", provider_name))
        
        max_tokens = max_tokens or config.max_tokens
        timeout = timeout or config.timeout

        logger.info(
            f"Calling {provider_name} model='{model_name}' "
            f"max_tokens={max_tokens} timeout={timeout}s"
        )

        try:
            response = await provider.send_prompt(
                prompt=prompt,
                model=model_name,
                max_tokens=max_tokens,
                timeout=timeout if provider_name == "ollama" else None,
            )
            response.model = model
            response.provider = provider_name
            
            logger.info(
                f"✓ {provider_name} response: "
                f"tokens={response.total_tokens} latency={response.latency_ms:.0f}ms"
            )
            
            return response
        except TimeoutError as e:
            logger.error(f"✗ Timeout on {provider_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ Error calling {provider_name}: {e}")
            raise

    def estimate_tokens(self, model: str, text: str) -> int:
        """
        Estimate token count for text.

        Uses provider-specific estimation (Rust-based if available).
        """
        provider_name, _ = self._detect_provider(model)

        if provider_name not in self.providers:
            logger.warning(f"Provider {provider_name} not found, using fallback estimation")
            return max(1, len(text) // 4)

        provider = self.providers[provider_name]
        tokens = provider.estimate_tokens(text)
        
        logger.debug(f"Estimated {tokens} tokens for {len(text)} chars ({provider_name})")
        return tokens

    def register_model(self, name: str, config: ModelConfig) -> None:
        """Register a custom model configuration."""
        self.model_configs[name] = config
        logger.info(f"Registered model: {name} ({config.provider})")

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            "claude": {
                "available": self.providers["claude"].client is not None,
                "has_api_key": bool(os.getenv("ANTHROPIC_API_KEY")),
            },
            "openai": {
                "available": self.providers["openai"].client is not None,
                "has_api_key": bool(os.getenv("OPENAI_API_KEY")),
            },
            "ollama": {
                "available": self.providers["ollama"].client is not None,
                "base_url": self.providers["ollama"].base_url,
            },
        }




# ============================================================================
# Global Service Instance & Helper Functions
# ============================================================================

_llm_service_instance: Optional[UnifiedLLMService] = None


def get_llm_service() -> UnifiedLLMService:
    """Get or create the global LLM service instance (singleton)."""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = UnifiedLLMService()
    return _llm_service_instance


async def call_llm(
    model: str,
    prompt: str,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None,
) -> LLMResponse:
    """
    Convenience function to call an LLM.

    Example:
        response = await call_llm("gpt-4", "What is AI?")
        print(response.content)
    """
    service = get_llm_service()
    return await service.call_llm(model, prompt, max_tokens, timeout)


def estimate_tokens(model: str, text: str) -> int:
    """
    Convenience function to estimate tokens for text.

    Example:
        tokens = estimate_tokens("gpt-4", "Your text here")
    """
    service = get_llm_service()
    return service.estimate_tokens(model, text)


# ============================================================================
# Module Initialization
# ============================================================================

logger.info("LLM Service module loaded")
logger.info(f"Rust token estimation: {'✓ enabled' if RUST_TOKENS_AVAILABLE else '⚠ disabled (using fallback)'}")
