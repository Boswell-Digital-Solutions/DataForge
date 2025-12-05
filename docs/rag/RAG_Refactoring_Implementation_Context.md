# RAG Pipeline Refactoring Implementation Context

**Version:** 1.0.0  
**Target:** VS Code with Claude Code Extension  
**Author:** Boswell Digital Solutions LLC  
**Date:** December 2024  
**Scope:** DataForge, NeuroForge, Rake + ForgeAgents Preparation  

---

## 🎯 Executive Summary

This refactoring implements production-grade RAG best practices across three cloud services (DataForge, NeuroForge, Rake) while preparing them for ForgeAgents orchestration. The changes are informed by current industry research on chunking strategies, vector indexing, and token budget management.

**Key Objective:** Make DataForge, NeuroForge, and Rake "agent-ready" for ForgeAgents coordination while improving retrieval quality and generation accuracy.

---

## 📊 Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLOUD SERVICES                               │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   DataForge     │  │   NeuroForge    │  │      Rake       │     │
│  │   Port 8001     │  │   Port 8000     │  │   Port 8002     │     │
│  │                 │  │                 │  │                 │     │
│  │ • PostgreSQL    │  │ • 5-stage LLM   │  │ • 5-stage       │     │
│  │   + pgvector    │  │   pipeline      │  │   ingestion     │     │
│  │ • 296 tests ✅  │  │ • Champion      │  │ • FETCH→CLEAN   │     │
│  │ • v5.2          │  │   model system  │  │   →CHUNK→EMBED  │     │
│  │ • 24 endpoints  │  │ • MCP toolchain │  │   →STORE        │     │
│  │ • Multi-AI      │  │ • Model scoring │  │ • 77 tests ✅   │     │
│  │   Learning API  │  │ • 100+ tests    │  │ • v1.0          │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           │                    │                    │               │
│           └────────────────────┼────────────────────┘               │
│                                │                                    │
│                    ┌───────────▼───────────┐                       │
│                    │    ForgeAgents        │ ← NEW ORCHESTRATION   │
│                    │    (Planned)          │                       │
│                    │ • Agent lifecycle     │                       │
│                    │ • Tool dispatch       │                       │
│                    │ • Policy enforcement  │                       │
│                    └───────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 REFACTORING TARGETS

### 1. Rake (Ingestion Pipeline) - CHUNK Stage Enhancement

**Current State:** Fixed-size chunking  
**Target State:** Semantic-aware chunking with metadata enrichment

#### Research-Backed Requirements

| Parameter | Current | Target | Rationale |
|-----------|---------|--------|-----------|
| Chunk Size | Variable | 250-500 tokens (~1000-2000 chars) | Optimal for embedding precision |
| Overlap | None/Fixed | 10-15% | Maintains semantic continuity |
| Strategy | Character-based | Semantic boundaries | Preserves meaning units |
| Metadata | Minimal | Rich (source, page, section, hierarchy) | Enables filtering |

#### Implementation Tasks

```python
# rake/services/chunker.py - Enhanced Chunking Service

class ChunkingStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    HIERARCHICAL = "hierarchical"
    HYBRID = "hybrid"  # Fixed with semantic boundaries

@dataclass
class ChunkConfig:
    strategy: ChunkingStrategy = ChunkingStrategy.HYBRID
    target_tokens: int = 350  # ~1400 chars, center of 250-500 range
    min_tokens: int = 100
    max_tokens: int = 500
    overlap_percent: float = 0.12  # 12% overlap
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True
    
@dataclass
class EnrichedChunk:
    content: str
    token_count: int
    metadata: dict  # source, page, section, hierarchy_path, chunk_index
    embedding: Optional[List[float]] = None
    semantic_score: Optional[float] = None  # Coherence score
```

#### Semantic Chunking Algorithm

```python
async def semantic_chunk(
    text: str, 
    config: ChunkConfig,
    embedding_model: str = "text-embedding-3-small"
) -> List[EnrichedChunk]:
    """
    Semantic-aware chunking:
    1. Split into sentences
    2. Generate sentence embeddings
    3. Detect semantic breakpoints via similarity drops
    4. Form chunks at breakpoints respecting size limits
    5. Add overlap at boundaries
    """
    sentences = split_into_sentences(text)
    embeddings = await batch_embed(sentences, embedding_model)
    
    # Detect semantic boundaries (similarity < threshold)
    boundaries = detect_semantic_boundaries(embeddings, threshold=0.7)
    
    # Form chunks respecting size constraints
    chunks = form_chunks_at_boundaries(
        sentences, 
        boundaries,
        min_tokens=config.min_tokens,
        max_tokens=config.max_tokens
    )
    
    # Add overlap
    chunks = add_overlap(chunks, config.overlap_percent)
    
    return chunks
```

---

### 2. DataForge (Knowledge Layer) - Vector Index Optimization

**Current State:** pgvector with HNSW  
**Target State:** Optimized HNSW + Reranking support + Hybrid search

#### Research-Backed Requirements

| Feature | Current | Target | Rationale |
|---------|---------|--------|-----------|
| Index Type | HNSW | HNSW (tuned) | Already optimal for scale |
| HNSW M | Default | 16-32 | Balance recall/memory |
| efConstruction | Default | 200 | Better graph quality |
| efSearch | Default | 100 | Sub-50ms @ 95%+ recall |
| Reranking | None | Cross-encoder rerank | Improves precision |
| Hybrid Search | None | Vector + BM25 | Exact match fallback |

#### Implementation Tasks

```python
# dataforge/services/vector_store.py - Enhanced Vector Operations

class VectorSearchConfig:
    # HNSW tuning
    hnsw_m: int = 24  # Connections per node
    hnsw_ef_construction: int = 200  # Build-time search width
    hnsw_ef_search: int = 100  # Query-time search width
    
    # Retrieval config
    top_k: int = 20  # Initial retrieval
    rerank_top_k: int = 5  # After reranking
    similarity_threshold: float = 0.7
    
    # Hybrid search
    enable_hybrid: bool = True
    bm25_weight: float = 0.3
    vector_weight: float = 0.7

async def hybrid_search(
    query: str,
    query_embedding: List[float],
    config: VectorSearchConfig,
    filters: Optional[dict] = None
) -> List[SearchResult]:
    """
    Hybrid search combining vector similarity + BM25 keyword matching.
    Enables exact-match requirements while preserving semantic search.
    """
    # Vector search
    vector_results = await pgvector_search(
        query_embedding, 
        top_k=config.top_k * 2,  # Over-retrieve for fusion
        ef_search=config.hnsw_ef_search
    )
    
    # BM25 search (if hybrid enabled)
    if config.enable_hybrid:
        bm25_results = await bm25_search(query, top_k=config.top_k)
        results = reciprocal_rank_fusion(
            vector_results, 
            bm25_results,
            weights=[config.vector_weight, config.bm25_weight]
        )
    else:
        results = vector_results
    
    # Optional reranking with cross-encoder
    if config.rerank_top_k:
        results = await rerank_with_cross_encoder(
            query, 
            results[:config.top_k],
            top_k=config.rerank_top_k
        )
    
    return results
```

#### ForgeAgents API Contract (DataForge)

```python
# ForgeAgents will call these endpoints:

@router.post("/v1/search")
async def agent_search(request: AgentSearchRequest) -> AgentSearchResponse:
    """
    ForgeAgents-compatible search endpoint.
    
    Request:
        query: str
        filters: Optional[dict]  # metadata filters
        top_k: int = 5
        include_metadata: bool = True
        rerank: bool = True
    
    Response:
        results: List[SearchResult]
        total_found: int
        search_latency_ms: float
        tokens_used: int  # For agent budget tracking
    """

@router.post("/v1/store")
async def agent_store(request: AgentStoreRequest) -> AgentStoreResponse:
    """Store agent memory/observations."""

@router.get("/v1/document/{doc_id}")
async def agent_get_document(doc_id: str) -> DocumentResponse:
    """Retrieve full document for agent context."""
```

---

### 3. NeuroForge (AI Orchestration) - Token Budget Management

**Current State:** Basic context assembly  
**Target State:** Model-aware token budgeting with graceful degradation

#### Research-Backed Requirements

| Model | Context Window | Target Budget | Safe Limit |
|-------|---------------|---------------|------------|
| Claude 3.5 | 200K | 100K | 50% rule |
| GPT-4o | 128K | 64K | 50% rule |
| GPT-4 Turbo | 128K | 64K | 50% rule |
| Llama 3.1 70B | 128K | 64K | 50% rule |
| Local (Ollama) | 8K-32K | 4K-16K | 50% rule |

**Critical Insight:** Studies show LLM performance degrades when input exceeds ~50% of context window.

#### Implementation Tasks

```python
# neuroforge/services/context_manager.py - Token Budget System

@dataclass
class ModelProfile:
    name: str
    context_window: int
    safe_input_limit: int  # 50% of context window
    cost_per_1k_input: float
    cost_per_1k_output: float
    supports_streaming: bool = True

MODEL_PROFILES = {
    "claude-3-5-sonnet": ModelProfile(
        name="claude-3-5-sonnet",
        context_window=200_000,
        safe_input_limit=100_000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015
    ),
    "gpt-4o": ModelProfile(
        name="gpt-4o",
        context_window=128_000,
        safe_input_limit=64_000,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015
    ),
    "llama-3.1-70b": ModelProfile(
        name="llama-3.1-70b",
        context_window=128_000,
        safe_input_limit=64_000,
        cost_per_1k_input=0.0,  # Local
        cost_per_1k_output=0.0
    ),
    "qwen2.5-coder-32b": ModelProfile(
        name="qwen2.5-coder-32b",
        context_window=32_000,
        safe_input_limit=16_000,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0
    )
}

@dataclass
class ContextBudget:
    """Token budget allocation with priorities."""
    total_limit: int
    system_tokens: int = 0      # Priority 1: System instructions
    user_tokens: int = 0        # Priority 2: User query
    context_tokens: int = 0     # Priority 3: Retrieved context
    history_tokens: int = 0     # Priority 4: Conversation history
    examples_tokens: int = 0    # Priority 5: Few-shot examples
    
    # Reserved for output
    output_reserve: int = 4000  # Default reserve for generation
    
    @property
    def remaining(self) -> int:
        used = (self.system_tokens + self.user_tokens + 
                self.context_tokens + self.history_tokens + 
                self.examples_tokens)
        return self.total_limit - used - self.output_reserve
    
    @property
    def occupancy_percent(self) -> float:
        used = (self.system_tokens + self.user_tokens + 
                self.context_tokens + self.history_tokens + 
                self.examples_tokens)
        return (used / self.total_limit) * 100

class ContextAssembler:
    """
    Assembles context within token budget using priority-based allocation.
    This is the enhanced PREPARE stage of the NeuroForge pipeline.
    """
    
    def __init__(self, model: str):
        self.profile = MODEL_PROFILES.get(model, MODEL_PROFILES["gpt-4o"])
        self.budget = ContextBudget(total_limit=self.profile.safe_input_limit)
        self.tokenizer = get_tokenizer(model)
    
    async def assemble(
        self,
        system_prompt: str,
        user_query: str,
        retrieved_chunks: List[EnrichedChunk],
        conversation_history: Optional[List[Message]] = None,
        examples: Optional[List[Example]] = None
    ) -> AssembledContext:
        """
        Priority-based context assembly:
        1. System prompt (always included)
        2. User query (always included)
        3. Retrieved context (truncated if needed)
        4. Conversation history (summarized if too long)
        5. Examples (dropped first if budget exceeded)
        """
        
        # Priority 1: System prompt
        self.budget.system_tokens = self._count_tokens(system_prompt)
        
        # Priority 2: User query
        self.budget.user_tokens = self._count_tokens(user_query)
        
        # Priority 5: Examples (allocate first, drop first)
        included_examples = []
        if examples and self.budget.remaining > 2000:
            for ex in examples:
                ex_tokens = self._count_tokens(ex.to_string())
                if self.budget.remaining - ex_tokens > 1000:
                    included_examples.append(ex)
                    self.budget.examples_tokens += ex_tokens
        
        # Priority 4: History (summarize if needed)
        included_history = []
        if conversation_history:
            history_str = self._format_history(conversation_history)
            history_tokens = self._count_tokens(history_str)
            
            if history_tokens > self.budget.remaining * 0.3:
                # Summarize older messages, keep recent
                history_str = await self._summarize_history(
                    conversation_history,
                    target_tokens=int(self.budget.remaining * 0.2)
                )
                history_tokens = self._count_tokens(history_str)
            
            self.budget.history_tokens = history_tokens
            included_history = history_str
        
        # Priority 3: Retrieved context (fill remaining budget)
        included_chunks = []
        for chunk in retrieved_chunks:
            chunk_tokens = self._count_tokens(chunk.content)
            if self.budget.remaining - chunk_tokens > 0:
                included_chunks.append(chunk)
                self.budget.context_tokens += chunk_tokens
            else:
                break  # Budget exhausted
        
        # Warn if occupancy > 70%
        if self.budget.occupancy_percent > 70:
            logger.warning(
                f"High context occupancy: {self.budget.occupancy_percent:.1f}%"
            )
        
        return AssembledContext(
            system_prompt=system_prompt,
            user_query=user_query,
            context_chunks=included_chunks,
            history=included_history,
            examples=included_examples,
            budget=self.budget,
            model_profile=self.profile
        )
```

#### ForgeAgents API Contract (NeuroForge)

```python
# ForgeAgents will call these endpoints:

@router.post("/v1/completion")
async def agent_completion(request: AgentCompletionRequest) -> AgentCompletionResponse:
    """
    ForgeAgents-compatible completion endpoint.
    Handles token budgeting automatically.
    
    Request:
        goal: str
        context: List[str]  # Retrieved chunks
        history: Optional[List[Message]]
        model: Optional[str]  # Override champion model
        max_tokens: Optional[int]
        temperature: float = 0.7
    
    Response:
        content: str
        model_used: str
        tokens_input: int
        tokens_output: int
        cost_cents: float
        latency_ms: float
    """

@router.post("/v1/agent_step")
async def run_agent_step(request: AgentStepRequest) -> AgentStepResponse:
    """
    Execute a single agent reasoning step.
    Used by ForgeAgents runtime for plan→act→observe→reflect loop.
    
    Request:
        agent_id: str
        step_type: StepType  # PLAN, ACT, OBSERVE, REFLECT
        context: AgentContext
        available_tools: List[ToolSpec]
    
    Response:
        reasoning: str
        action: Optional[ToolCall]
        should_continue: bool
        confidence: float
    """
```

---

## 🤖 ForgeAgents Integration Points

The refactoring prepares all three services for ForgeAgents orchestration:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FORGEAGENTS RUNTIME                             │
│                                                                      │
│  Agent Lifecycle: PLAN → ACT → OBSERVE → REFLECT → [NEXT/FINISH]   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    TOOL DISPATCH LAYER                       │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ DataForge    │  │ NeuroForge   │  │    Rake      │      │   │
│  │  │ Adapter      │  │ Adapter      │  │ Adapter      │      │   │
│  │  │              │  │              │  │              │      │   │
│  │  │ • search     │  │ • completion │  │ • enqueue    │      │   │
│  │  │ • store      │  │ • agent_step │  │ • status     │      │   │
│  │  │ • get_doc    │  │ • score      │  │ • retry      │      │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │   │
│  │         │                 │                 │               │   │
│  └─────────┼─────────────────┼─────────────────┼───────────────┘   │
│            │                 │                 │                    │
│            ▼                 ▼                 ▼                    │
│      DataForge API     NeuroForge API      Rake API                │
│      (Port 8001)       (Port 8000)         (Port 8002)             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### ForgeAgents Tool Contracts

```python
# forgeagents/tools/dataforge_tools.py

class DataForgeSearchTool(BaseTool):
    name = "dataforge_search"
    description = "Search knowledge base for relevant information"
    
    input_schema = {
        "query": {"type": "string", "description": "Search query"},
        "top_k": {"type": "integer", "default": 5},
        "filters": {"type": "object", "optional": True}
    }
    
    async def execute(self, input: dict) -> ToolResult:
        response = await dataforge_client.search(
            query=input["query"],
            top_k=input.get("top_k", 5),
            filters=input.get("filters")
        )
        return ToolResult(
            success=True,
            data=response.results,
            tokens_used=response.tokens_used
        )

class NeuroForgeCompletionTool(BaseTool):
    name = "neuroforge_completion"
    description = "Generate text using LLM with automatic context management"
    
    input_schema = {
        "goal": {"type": "string", "description": "What to generate"},
        "context": {"type": "array", "items": {"type": "string"}},
        "temperature": {"type": "number", "default": 0.7}
    }

class RakeIngestTool(BaseTool):
    name = "rake_ingest"
    description = "Ingest documents into knowledge base"
    
    input_schema = {
        "source_type": {"type": "string", "enum": ["url", "file", "api"]},
        "source": {"type": "string"},
        "metadata": {"type": "object", "optional": True}
    }
```

---

## 📋 Implementation Phases

### Phase 1: Rake Chunking Enhancement (Week 1)

```
□ Task 1.1: Implement ChunkingStrategy enum and ChunkConfig dataclass
□ Task 1.2: Create semantic boundary detection using sentence embeddings
□ Task 1.3: Implement overlap logic for chunk boundaries
□ Task 1.4: Add metadata enrichment (source, page, section, hierarchy)
□ Task 1.5: Create chunking strategy factory (FIXED, SEMANTIC, HYBRID)
□ Task 1.6: Write tests for each chunking strategy
□ Task 1.7: Benchmark chunk quality metrics (coherence, retrieval recall)
```

### Phase 2: DataForge Vector Optimization (Week 1-2)

```
□ Task 2.1: Tune HNSW parameters (M=24, ef_construction=200, ef_search=100)
□ Task 2.2: Implement hybrid search (vector + BM25)
□ Task 2.3: Add cross-encoder reranking support
□ Task 2.4: Create AgentSearchRequest/Response schemas
□ Task 2.5: Implement /v1/search endpoint for ForgeAgents
□ Task 2.6: Implement /v1/store endpoint for agent memory
□ Task 2.7: Add latency and token tracking to responses
□ Task 2.8: Write integration tests for search accuracy
```

### Phase 3: NeuroForge Token Budget System (Week 2)

```
□ Task 3.1: Create ModelProfile dataclass with context limits
□ Task 3.2: Implement ContextBudget with priority allocation
□ Task 3.3: Build ContextAssembler for the PREPARE stage
□ Task 3.4: Add history summarization for long conversations
□ Task 3.5: Implement graceful degradation (drop examples first)
□ Task 3.6: Add occupancy warnings (>70% threshold)
□ Task 3.7: Create /v1/completion endpoint for ForgeAgents
□ Task 3.8: Create /v1/agent_step endpoint for agent runtime
□ Task 3.9: Write tests for token budget scenarios
```

### Phase 4: Integration Testing (Week 3)

```
□ Task 4.1: End-to-end test: Rake → DataForge → NeuroForge
□ Task 4.2: Test retrieval quality with new chunking
□ Task 4.3: Test token budget under various model profiles
□ Task 4.4: Test hybrid search accuracy vs pure vector
□ Task 4.5: Benchmark latency targets (<50ms retrieval, <2s generation)
□ Task 4.6: Document API contracts for ForgeAgents team
```

### Phase 5: ForgeAgents Preparation (Week 4)

```
□ Task 5.1: Create tool adapter interfaces
□ Task 5.2: Implement DataForge tool adapter
□ Task 5.3: Implement NeuroForge tool adapter  
□ Task 5.4: Implement Rake tool adapter
□ Task 5.5: Write tool contract tests
□ Task 5.6: Create ForgeAgents integration guide
```

---

## 🧪 Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Retrieval Recall@5 | Unknown | >90% | Test set evaluation |
| Retrieval Latency P95 | Unknown | <50ms | DataForge metrics |
| Token Budget Accuracy | N/A | 100% | Never exceed safe limit |
| Chunk Coherence | Unknown | >0.8 | Semantic similarity score |
| Generation Quality | Baseline | +15% | Human eval on test set |
| Cost per Query | Baseline | -20% | Token tracking |

---

## 🚀 Ready-to-Use Claude Code Prompt

Copy the following prompt into Claude Code to begin implementation:

---

# IMPLEMENTATION PROMPT FOR CLAUDE CODE

```
You are implementing RAG pipeline optimizations for the Forge Ecosystem.

## Context
- DataForge: PostgreSQL + pgvector knowledge store (Port 8001, v5.2, 296 tests)
- NeuroForge: AI orchestration with 5-stage pipeline (Port 8000, 100+ tests)  
- Rake: Document ingestion pipeline (Port 8002, v1.0, 77 tests)
- All services preparing for ForgeAgents orchestration layer

## Your Task
Implement the RAG refactoring in phases, starting with Rake chunking enhancement.

## Phase 1: Enhanced Chunking for Rake

### Step 1: Create the chunking types
Location: `rake/models/chunking.py`

Create:
- ChunkingStrategy enum (FIXED_SIZE, SEMANTIC, HIERARCHICAL, HYBRID)
- ChunkConfig dataclass with target_tokens=350, overlap_percent=0.12
- EnrichedChunk dataclass with content, token_count, metadata, embedding

### Step 2: Implement semantic chunking service
Location: `rake/services/chunker.py`

Implement:
- split_into_sentences() - NLP sentence boundary detection
- detect_semantic_boundaries() - Find similarity drops between sentences
- form_chunks_at_boundaries() - Create chunks respecting size limits
- add_overlap() - Add 10-15% overlap at chunk boundaries
- semantic_chunk() - Main async function combining above

### Step 3: Update the CHUNK pipeline stage
Location: `rake/pipeline/stages/chunk.py`

Modify the existing chunk stage to:
- Accept ChunkConfig parameter
- Support strategy selection (FIXED, SEMANTIC, HYBRID)
- Enrich chunks with metadata (source, page, section)
- Return List[EnrichedChunk]

### Step 4: Write tests
Location: `rake/tests/test_chunking.py`

Test cases:
- Fixed-size chunking respects token limits
- Semantic chunking detects topic boundaries
- Overlap is correctly applied
- Metadata is preserved through pipeline
- Empty/edge cases handled

## Code Style
- Use Python 3.11+ features
- Type hints on all functions
- Async where I/O involved
- Pydantic for data validation
- Comprehensive docstrings

## After Each Step
- Run existing tests to ensure no regression
- Commit with descriptive message
- Report what you implemented and any issues

Begin with Step 1. Show me the code for `rake/models/chunking.py`.
```

---

## 📚 Reference Documents

### From Project Knowledge
- Forge Ecosystem Master Map
- DataForge README (v5.2)
- NeuroForge README  
- Rake README (v1.0)
- ForgeAgents Implementation Plan

### From RAG Research
- Chunking: 250-500 tokens optimal, 10-15% overlap
- Vector Indexing: HNSW with M=24, ef=100-200 for sub-50ms
- Token Budget: Stay under 50% of context window
- Hybrid Search: 70% vector + 30% BM25 weight
- Reranking: Cross-encoder improves precision significantly

---

*Document generated for Claude Code implementation.*  
*Boswell Digital Solutions LLC © 2024*
