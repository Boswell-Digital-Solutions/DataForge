# ForgeAgents 120-Skill API Registry

**Version:** 1.0  
**Status:** Production Ready  
**Organization:** Boswell Digital Solutions LLC  
**Updated:** December 2025

---

## Overview

ForgeAgents is a **skill/capability library** containing **120 domain-specific operations** exposed via REST API. Each skill is a reusable, independently callable unit of AI-enhanced functionality.

**Architecture:**
```
ForgeAgents Backend
│
├─ API Layer (REST endpoints)
├─ 120 Skill Implementations
├─ MAPO Orchestration Integration
├─ NeuroForge Model Routing
└─ Access Control (PUBLIC vs BDS_ONLY)

Consumed by:
├─ VibeForge (public) → 45 skills
└─ VibeForge_BDS (internal) → 120 skills
```

---

## Section V1: Fundamentals (Agents 1-30)

### Section A: Learning & Understanding (6 Skills)

#### A1 — 80/20 Extractor
- **Purpose:** Extract essential 20% of information from complex topics
- **Input:** `topic: string`
- **Output:** Summary with core concepts, ignore edge cases
- **Access:** PUBLIC
- **Use Case:** Developers quickly learning new technologies

#### A2 — Skill in 30 Days
- **Purpose:** Generate structured 30-day learning roadmap
- **Input:** `skill: string`
- **Output:** Weekly breakdown with specific exercises
- **Access:** PUBLIC
- **Use Case:** Self-directed learning planning

#### A3 — Explain Like I'm 12
- **Purpose:** Simplify concepts for beginners
- **Input:** `topic: string`
- **Output:** Simple explanation + metaphors + 3 confirmation questions
- **Access:** PUBLIC
- **Use Case:** Non-technical stakeholder communication

#### A4 — Problem Solver
- **Purpose:** Break problems into actionable steps
- **Input:** `problem: string`
- **Output:** Step-by-step solution path
- **Access:** PUBLIC
- **Use Case:** Technical troubleshooting, algorithm design

#### A6 — Knowledge Tester
- **Purpose:** Generate and evaluate learning
- **Input:** `topic: string`
- **Output:** 10 questions + evaluation of answers + gap analysis
- **Access:** PUBLIC
- **Use Case:** Reinforcement learning, self-assessment

#### A7 — Memory Booster
- **Purpose:** Create memorable mental models
- **Input:** `topic: string`
- **Output:** Metaphors + stories + visualization
- **Access:** PUBLIC
- **Use Case:** Knowledge retention, teaching

---

### Section B: Architecture, Design, UX (7 Skills)

#### B1 — Architecture Breaker
- **Purpose:** Decompose systems into modules
- **Input:** `project: string, description: string`
- **Output:** Module breakdown, data flows, API boundaries, dependencies
- **Access:** PUBLIC
- **Use Case:** System design, feature planning

#### B2 — API Designer
- **Purpose:** Design REST/RPC endpoints
- **Input:** `feature: string, context: string`
- **Output:** Endpoints with routes, params, response shapes, validations
- **Access:** PUBLIC
- **Use Case:** API specification, backend design

#### B5 — Edge-Case Generator
- **Purpose:** Identify failure scenarios
- **Input:** `feature: string, context: string`
- **Output:** List of edge cases, boundary conditions, failure modes
- **Access:** PUBLIC
- **Use Case:** QA planning, robustness testing

#### B6 — UX Theory Translator
- **Purpose:** Formalize informal UX ideas
- **Input:** `ui_idea: string`
- **Output:** UX principles, heuristics applied, formal specifications
- **Access:** PUBLIC
- **Use Case:** UX documentation, design review

#### B7 — Cognitive Load Reducer
- **Purpose:** Minimize user/reader friction
- **Input:** `text: string` or `ui_spec: string`
- **Output:** Simplified version with reduced complexity
- **Access:** PUBLIC
- **Use Case:** UX improvement, documentation clarity

#### B8 — Threat Modeling (Lite)
- **Purpose:** Identify attack surfaces
- **Input:** `architecture: string`
- **Output:** High-level threats, mitigations (general security only)
- **Access:** PUBLIC
- **Restriction:** General architecture patterns only, no proprietary systems
- **Use Case:** Security threat assessment

#### B? — Interaction Pattern Helper
- **Purpose:** Recommend UX patterns
- **Input:** `use_case: string`
- **Output:** Pattern recommendations (cards, lists, wizards, modals, etc.)
- **Access:** PUBLIC
- **Use Case:** UI component selection

---

### Section C: Editing, Refinement & Writing (5 Skills)

#### C2 — Refinement Judge
- **Purpose:** Compare alternatives and merge best parts
- **Input:** `option_a: string, option_b: string, ..., criteria: string`
- **Output:** Merged superior result with justification
- **Access:** PUBLIC
- **Use Case:** Iterative improvement, variant comparison

#### C3 — Critic Agent
- **Purpose:** Provide constructive critique
- **Input:** `answer: string, context: string`
- **Output:** Weaknesses + specific improvement suggestions
- **Access:** PUBLIC
- **Use Case:** Review feedback, quality improvement

#### C4 — Final-Pass Editor
- **Purpose:** Polish for professionalism
- **Input:** `text: string, tone: string (optional)`
- **Output:** Refined text with improved clarity, grammar, tone
- **Access:** PUBLIC
- **Use Case:** Documentation, marketing copy, communication

#### C6 — Intent Detector
- **Purpose:** Classify user intent and route appropriately
- **Input:** `request: string`
- **Output:** Intent category + recommended agents to use
- **Access:** PUBLIC
- **Use Case:** Agent routing, workflow optimization

#### C5 — Persona Optimizer
- **Purpose:** Maintain voice consistency
- **Input:** `text: string, persona: string`
- **Output:** Text rewritten with consistent voice
- **Access:** PUBLIC
- **Use Case:** Content consistency, brand voice

---

### Section E: Branding & Tone (2 Skills)

#### E2 — Identity Consistency
- **Purpose:** Maintain project brand alignment
- **Input:** `text: string, brand_guidelines: string`
- **Output:** Text checked for consistency + corrections
- **Access:** PUBLIC
- **Use Case:** Brand consistency, editorial standards

#### E? — Project Fit Analyzer
- **Purpose:** Evaluate idea alignment with project goals
- **Input:** `idea: string, project_goals: string`
- **Output:** Fit assessment, alignment score, suggestions
- **Access:** PUBLIC
- **Restriction:** Project-level only, no Forge ecosystem references
- **Use Case:** Feature evaluation, prioritization

---

### Section F: Safety, Privacy, Policy (3 Skills)

#### F1 — Prompt Safety Inspector
- **Purpose:** Detect potential abuse/jailbreak vectors
- **Input:** `prompt: string`
- **Output:** Risk assessment + recommendations
- **Access:** PUBLIC (with restrictions)
- **Use Case:** Prompt safety validation

#### F2 — Data Privacy Annotator
- **Purpose:** Detect and protect PII
- **Input:** `text: string`
- **Output:** PII identified + safe rewrite
- **Access:** PUBLIC
- **Use Case:** Privacy compliance, data protection

#### F3 — SAS Enforcement (Public Version)
- **Purpose:** Basic safety and standards check
- **Input:** `request: string, context: string`
- **Output:** Safety assessment + recommendations
- **Access:** PUBLIC (limited)
- **Restriction:** General best practices only, not proprietary SAS rules
- **Use Case:** Quality standards, safety basics

---

## Section V2: Advanced Skills (Agents 31-60)

### Section G: Advanced Learning & Research (7 Skills)

#### G1 — Depth Analyzer
- **Purpose:** Surface deeper theory and academic context
- **Input:** `topic: string`
- **Output:** Academic foundations, theoretical background, key sources
- **Access:** PUBLIC
- **Use Case:** Research, comprehensive learning

#### G2 — Learning Path Customizer
- **Purpose:** Adapt learning to skill level
- **Input:** `skill: string, level: enum(beginner, intermediate, advanced)`
- **Output:** Customized learning path for level
- **Access:** PUBLIC
- **Use Case:** Adaptive learning, personalization

#### G3 — Parallel Concept Mapper
- **Purpose:** Relate topic to similar concepts
- **Input:** `topic: string`
- **Output:** Related concepts + differences + application contexts
- **Access:** PUBLIC
- **Use Case:** Conceptual understanding, knowledge synthesis

#### G4 — Common Pitfalls Finder
- **Purpose:** Identify beginner mistakes
- **Input:** `topic: string`
- **Output:** Common mistakes + prevention strategies
- **Access:** PUBLIC
- **Use Case:** Error prevention, expertise building

#### G5 — Confusion Detector
- **Purpose:** Predict and resolve confusion points
- **Input:** `topic: string`
- **Output:** Likely confusion points + detailed explanations
- **Access:** PUBLIC
- **Use Case:** Teaching, documentation clarity

#### G6 — Memory Flashcards Generator
- **Purpose:** Create spaced repetition materials
- **Input:** `topic: string`
- **Output:** Flashcard set (term, definition, example)
- **Access:** PUBLIC
- **Use Case:** Study materials, knowledge reinforcement

#### G7 — Explain Like Professionals Do
- **Purpose:** Advanced expert-level explanation
- **Input:** `topic: string`
- **Output:** Explanation for industry experts
- **Access:** PUBLIC
- **Use Case:** Senior developer onboarding, expert communication

---

### Section H: AI/Model/Agent Engineering (7 Skills)

#### H1 — Fine-Tuning Roadmap
- **Purpose:** Plan model fine-tuning
- **Input:** `task: string, dataset_size: int (optional)`
- **Output:** Steps, data formats, evaluation metrics, resource requirements
- **Access:** PUBLIC
- **Use Case:** Model customization planning

#### H2 — Prompt Robustness Tester
- **Purpose:** Stress-test prompts
- **Input:** `prompt: string`
- **Output:** Edge cases, adversarial variants, robustness assessment
- **Access:** PUBLIC
- **Use Case:** Prompt validation, reliability testing

#### H3 — Agent Chain Designer (Lite)
- **Purpose:** Design multi-step reasoning (simple)
- **Input:** `goal: string, constraints: string (optional)`
- **Output:** Agent sequence, hand-off conditions, fallbacks
- **Access:** PUBLIC
- **Restriction:** Simple chains only, not Forge orchestration pipelines
- **Use Case:** Workflow design, prompt engineering

#### H4 — Multi-LLM Fusion Specialist
- **Purpose:** Combine outputs from multiple models
- **Input:** `outputs: string[], task: string`
- **Output:** Unified merged answer with quality assessment
- **Access:** PUBLIC
- **Use Case:** Ensemble prompting, result reconciliation

#### H5 — Embeddings Explainer
- **Purpose:** Explain embedding strategies
- **Input:** `domain: string, use_case: string`
- **Output:** Embedding approach explanation + examples + semantic logic
- **Access:** PUBLIC
- **Use Case:** Vector search understanding, RAG strategy

#### H6 — RAG Optimizer (Public)
- **Purpose:** Design retrieval-augmented generation
- **Input:** `use_case: string, data_volume: string (optional)`
- **Output:** Best RAG approach, chunking, retrieval, reranking strategy
- **Access:** PUBLIC
- **Use Case:** RAG pipeline design

#### H7 — Prompt-to-Data Generator
- **Purpose:** Create synthetic training data
- **Input:** `class: string, count: int (optional)`
- **Output:** Synthetic samples with labels + safety review
- **Access:** PUBLIC
- **Use Case:** Dataset generation, model training prep

---

### Section I: Development/Code/Infrastructure (7 Skills)

#### I1 — Clean Code Rewriter
- **Purpose:** Improve code quality
- **Input:** `code: string, language: string`
- **Output:** Refactored code + explanation of improvements
- **Access:** PUBLIC
- **Use Case:** Code review, maintainability improvement

#### I2 — Bug Reproduction Agent
- **Purpose:** Diagnose errors
- **Input:** `error: string, context: string (optional)`
- **Output:** Likely reproduction steps + root cause hypotheses
- **Access:** PUBLIC
- **Use Case:** Debugging, issue triage

#### I3 — Performance Bottleneck Analysis
- **Purpose:** Identify performance issues
- **Input:** `code: string, metrics: string (optional)`
- **Output:** Bottleneck identification + optimization recommendations
- **Access:** PUBLIC
- **Use Case:** Optimization, profiling guidance

#### I4 — API Mock Generator
- **Purpose:** Create test mock responses
- **Input:** `endpoint: string, spec: string (optional)`
- **Output:** Realistic mock response JSON
- **Access:** PUBLIC
- **Use Case:** Testing, API contract testing

#### I5 — CI/CD Advisor
- **Purpose:** Design deployment pipelines
- **Input:** `tech_stack: string, requirements: string`
- **Output:** Pipeline stages, test automation, deployment steps
- **Access:** PUBLIC
- **Use Case:** DevOps planning, automation design

#### I6 — Infrastructure as Code Generator
- **Purpose:** Generate infrastructure code
- **Input:** `infrastructure: string, tool: enum(terraform, pulumi)`
- **Output:** IaC template for infrastructure
- **Access:** PUBLIC
- **Use Case:** Infrastructure automation, cloud setup

#### I7 — Container Strategy Designer
- **Purpose:** Design Docker/Kubernetes setup
- **Input:** `service: string, requirements: string`
- **Output:** Dockerfile + docker-compose.yml structure recommendations
- **Access:** PUBLIC
- **Use Case:** Containerization strategy, Docker setup

---

### Section J: UX/Accessibility (7 Skills)

#### J1 — UX Critique Agent
- **Purpose:** Evaluate UX against heuristics
- **Input:** `ui_design: string` or `flow_description: string`
- **Output:** Heuristic violations + usability issues + fixes
- **Access:** PUBLIC
- **Use Case:** Design review, UX validation

#### J2 — Accessibility Checker
- **Purpose:** Identify a11y issues
- **Input:** `ui: string` or `content: string`
- **Output:** A11y violations (WCAG) + remediation suggestions
- **Access:** PUBLIC
- **Use Case:** Accessibility compliance, inclusive design

#### J3 — Cognitive Load UX Rewrite
- **Purpose:** Simplify UX copy
- **Input:** `ui_copy: string`
- **Output:** Simplified, clearer copy with reduced friction
- **Access:** PUBLIC
- **Use Case:** Usability improvement, copy refinement

#### J4 — Component Library Selector
- **Purpose:** Recommend UI libraries
- **Input:** `tech_stack: string, requirements: string`
- **Output:** Library recommendations with pros/cons comparison
- **Access:** PUBLIC
- **Use Case:** Technology selection, UI framework evaluation

#### J5 — Interaction Pattern Advisor
- **Purpose:** Recommend UX patterns
- **Input:** `use_case: string`
- **Output:** Pattern recommendations (cards, lists, wizards, modals, etc.)
- **Access:** PUBLIC
- **Use Case:** UX pattern selection

#### J6 — Dark Mode Optimizer
- **Purpose:** Improve dark mode readability
- **Input:** `ui_design: string` or `color_palette: string`
- **Output:** Dark mode optimizations, contrast improvements
- **Access:** PUBLIC
- **Use Case:** Theme design, accessibility for dark mode

#### J7 — Microcopy Writer
- **Purpose:** Generate UX microcopy
- **Input:** `context: string, element: string (label, tooltip, button, etc.)`
- **Output:** Effective, concise microcopy
- **Access:** PUBLIC
- **Use Case:** UI labels, onboarding copy, help text

---

### Section K: Product/Business (2 Skills)

#### K1 — Market Category Finder
- **Purpose:** Determine market positioning
- **Input:** `product: string, description: string`
- **Output:** Market category + positioning narrative
- **Access:** PUBLIC
- **Use Case:** Product positioning, market analysis

#### K2 — Business Model Generator
- **Purpose:** Suggest monetization strategies
- **Input:** `product: string, market: string (optional)`
- **Output:** Monetization options with comparison (freemium, paid, SaaS, enterprise)
- **Access:** PUBLIC
- **Use Case:** Business model selection, pricing strategy

---

## Section V3: Operations & Infrastructure (Agents 61-90)

### Section L: MAPO & Orchestration (7 Skills) — **BDS ONLY**

#### L1 — MAPO Pipeline Designer
- **Purpose:** Design orchestration pipelines
- **Input:** `request: string, constraints: string (optional)`
- **Output:** MAPO pipeline (moderation, access, policy, orchestration)
- **Access:** BDS_ONLY
- **Use Case:** Workflow design, agent orchestration

#### L2 — Policy Validator
- **Purpose:** SAS compliance checking
- **Input:** `action: string, context: string`
- **Output:** Policy violations detected + remediation
- **Access:** BDS_ONLY
- **Use Case:** SAS rule enforcement

#### L3 — Local vs Cloud Decider
- **Purpose:** Route to local or cloud models
- **Input:** `task: string, requirements: string`
- **Output:** Decision + tradeoff analysis (latency, cost, privacy)
- **Access:** BDS_ONLY
- **Use Case:** Model selection, optimization

#### L4 — Champion Routing Agent
- **Purpose:** Select champion model
- **Input:** `task: string, available_models: string[]`
- **Output:** Champion model selection + justification
- **Access:** BDS_ONLY
- **Use Case:** Model routing, performance optimization

#### L5 — Multimodel Conflict Resolver
- **Purpose:** Reconcile disagreements between models
- **Input:** `model_outputs: {model: string, output: string}[]`
- **Output:** Consensus merged output + confidence score
- **Access:** BDS_ONLY
- **Use Case:** Ensemble resolution, reliability

#### L6 — Orchestration Blueprint Agent
- **Purpose:** Plan complex multi-LLM workflows
- **Input:** `goal: string, constraints: string (optional)`
- **Output:** Multi-step sequence with hand-offs and fallbacks
- **Access:** BDS_ONLY
- **Use Case:** Complex workflow design

#### L7 — Policy-Aware Refiner
- **Purpose:** Enforce safety under constraints
- **Input:** `text: string, policies: string[]`
- **Output:** Refined text compliant with all policies
- **Access:** BDS_ONLY
- **Use Case:** Safety enforcement, policy compliance

---

### Section M: Vision/Video/Multimodal (7 Skills) — **BDS ONLY**

#### M1 — Sora Prompt Architect
- **Purpose:** Generate cinematic video prompts
- **Input:** `theme: string, style: string (optional)`
- **Output:** Sora-optimized prompt with cinematic details
- **Access:** BDS_ONLY
- **Use Case:** Video generation, creative production

#### M2 — Storyboard Generator
- **Purpose:** Break scenes into frames
- **Input:** `scene: string` or `script: string`
- **Output:** Storyboard with shot types and transitions
- **Access:** BDS_ONLY
- **Use Case:** Video planning, creative direction

#### M3 — Cinematic Tag Enhancer
- **Purpose:** Enhance prompts with cinematic vocabulary
- **Input:** `prompt: string`
- **Output:** Enhanced prompt with lens, exposure, color, motion tags
- **Access:** BDS_ONLY
- **Use Case:** Video quality, aesthetic direction

#### M4 — Character Consistency Agent
- **Purpose:** Maintain character consistency
- **Input:** `character_description: string`
- **Output:** Consistency rules + variant prompts
- **Access:** BDS_ONLY
- **Use Case:** Multi-shot character consistency

#### M5 — Scene→Prompt Converter
- **Purpose:** Convert story to video prompt
- **Input:** `scene: string`
- **Output:** Video prompt with camera direction
- **Access:** BDS_ONLY
- **Use Case:** Narrative to visual conversion

#### M6 — Multi-Shot Sequencer
- **Purpose:** Generate shot sequences
- **Input:** `narrative: string`, `shot_count: int`
- **Output:** Sequence of shots matching narrative flow
- **Access:** BDS_ONLY
- **Use Case:** Video production, cinematography

#### M7 — Voice + Subtitle Planner
- **Purpose:** Plan narration and subtitles
- **Input:** `scene: string` or `video_description: string`
- **Output:** Narration suggestions + subtitle lines
- **Access:** BDS_ONLY
- **Use Case:** Video post-production, accessibility

---

### Section N: DataForge/Rake/Knowledge (7 Skills) — **BDS ONLY**

#### N1 — Ingestion Blueprint
- **Purpose:** Plan data ingestion
- **Input:** `data_source: string, format: string`
- **Output:** Rake pipeline stages (FETCH, CLEAN, CHUNK, EMBED, STORE)
- **Access:** BDS_ONLY
- **Use Case:** Data pipeline design

#### N2 — Vector Schema Designer
- **Purpose:** Design embedding schema
- **Input:** `data_type: string, use_cases: string[]`
- **Output:** Vector schema with metadata fields
- **Access:** BDS_ONLY
- **Use Case:** Vector database design, RAG setup

#### N3 — Retrieval Strategy Selector
- **Purpose:** Choose retrieval approach
- **Input:** `use_case: string, data_characteristics: string`
- **Output:** Retrieval strategy (hybrid, semantic, keyword, reranker)
- **Access:** BDS_ONLY
- **Use Case:** RAG optimization

#### N4 — RAG Failure Diagnoser
- **Purpose:** Debug retrieval failures
- **Input:** `failure_description: string, chunks: string[], query: string`
- **Output:** Root cause analysis + fixes
- **Access:** BDS_ONLY
- **Use Case:** RAG troubleshooting

#### N5 — Eval Suite Generator
- **Purpose:** Create evaluation tests
- **Input:** `retrieval_task: string`
- **Output:** Test suite for evaluating retrieval accuracy
- **Access:** BDS_ONLY
- **Use Case:** RAG quality assurance

#### N6 — Data-to-Prompt Agent
- **Purpose:** Format retrieved data for prompts
- **Input:** `chunks: string[]`, `task: string`
- **Output:** Coherent prompt context from chunks
- **Access:** BDS_ONLY
- **Use Case:** RAG prompt preparation

#### N7 — Chunking Strategy Advisor
- **Purpose:** Design chunking approach
- **Input:** `dataset: string`, `use_case: string`
- **Output:** Chunking parameters (size, overlap, heuristics)
- **Access:** BDS_ONLY
- **Use Case:** RAG optimization, indexing strategy

---

### Section O: NeuroForge/Model Strategy (9 Skills) — **BDS ONLY**

#### O1 — Champion Model Criteria
- **Purpose:** Define model selection rules
- **Input:** `task_type: string`, `requirements: string`
- **Output:** Selection criteria (latency, reasoning, safety, cost)
- **Access:** BDS_ONLY
- **Use Case:** Model ranking strategy

#### O2 — Fallback Layer Advisor
- **Purpose:** Design fallback model chains
- **Input:** `primary_model: string`, `constraints: string`
- **Output:** Fallback sequence with routing logic
- **Access:** BDS_ONLY
- **Use Case:** Reliability engineering, graceful degradation

#### O3 — Scoring Metric Designer
- **Purpose:** Design quality metrics
- **Input:** `task_type: string`
- **Output:** Metrics for model response evaluation
- **Access:** BDS_ONLY
- **Use Case:** Model evaluation, quality measurement

#### O4 — Error-Resilience Evaluator
- **Purpose:** Assess model robustness
- **Input:** `model: string`, `test_cases: string[]`
- **Output:** Robustness score + failure modes
- **Access:** BDS_ONLY
- **Use Case:** Model reliability assessment

#### O5 — Multi-Turn Memory Planner
- **Purpose:** Plan conversation memory strategy
- **Input:** `conversation_length: int`, `context_needs: string`
- **Output:** Memory strategy (full, sliding window, summarization)
- **Access:** BDS_ONLY
- **Use Case:** Long conversation handling

#### O6 — Privacy-Preserving Mode
- **Purpose:** Apply privacy transformations
- **Input:** `text: string`, `sensitivity: enum(low, medium, high)`
- **Output:** Privacy-transformed text (pseudonymization, redaction)
- **Access:** BDS_ONLY
- **Use Case:** Privacy compliance, secure processing

#### O7 — Model Comparison Explainer
- **Purpose:** Explain model differences
- **Input:** `model_a: string`, `model_b: string`
- **Output:** Architecture differences, training data, strengths comparison
- **Access:** BDS_ONLY
- **Use Case:** Model selection, understanding capabilities

#### O8 — Compute Optimizer
- **Purpose:** Optimize inference efficiency
- **Input:** `task: string`, `constraints: string (optional)`
- **Output:** Recommendations (token optimization, temp, length limits)
- **Access:** BDS_ONLY
- **Use Case:** Cost optimization, performance tuning

#### O9 — Local Model Prioritizer
- **Purpose:** Prefer local execution
- **Input:** `task: string`, `available_local_models: string[]`
- **Output:** Local-first strategy with fallback
- **Access:** BDS_ONLY
- **Use Case:** Privacy-first architecture, latency optimization

---

## Section V4: Ecosystem & Governance (Agents 91-120)

### Section P: Security/Safety/Reliability (7 Skills) — **BDS ONLY**

#### P1 — Auth & Roles Designer
- **Purpose:** Design access control
- **Input:** `system: string`, `user_types: string[]`
- **Output:** Auth roles + permissions + scopes
- **Access:** BDS_ONLY
- **Use Case:** Security architecture, access control

#### P2 — Threat Vector Expansion
- **Purpose:** Identify attack surfaces
- **Input:** `system: string`, `architecture: string (optional)`
- **Output:** Expanded threat list + model-specific exploits
- **Access:** BDS_ONLY
- **Use Case:** Security audit, threat modeling

#### P3 — Data Redaction Planner
- **Purpose:** Plan data protection
- **Input:** `data_schema: string`, `sensitivity: string`
- **Output:** Redaction rules + PII protection strategy
- **Access:** BDS_ONLY
- **Use Case:** Data security, privacy protection

#### P4 — Abuse Prevention Advisor
- **Purpose:** Predict misuse scenarios
- **Input:** `feature: string`, `target_users: string`
- **Output:** Misuse scenarios + prevention measures
- **Access:** BDS_ONLY
- **Use Case:** Feature safety, abuse prevention

#### P5 — Predictable Behavior Agent
- **Purpose:** Stabilize behavior
- **Input:** `task: string`, `variability_issue: string (optional)`
- **Output:** Constraints + deterministic patterns
- **Access:** BDS_ONLY
- **Use Case:** Reliability, consistency

#### P6 — Guardrail Explainer
- **Purpose:** Design safety guardrails
- **Input:** `use_case: string`, `risks: string (optional)`
- **Output:** Guardrails + reasoning discipline + output limits
- **Access:** BDS_ONLY
- **Use Case:** Safety engineering

#### P7 — Rate-Limit Strategy
- **Purpose:** Design rate limiting
- **Input:** `system: string`, `workload_types: string[]`
- **Output:** Rate limit rules by tenant/role/workload
- **Access:** BDS_ONLY
- **Use Case:** Capacity planning, fair-use enforcement

---

### Section Q: Persona/Tone/Narrative (7 Skills)

#### Q1 — Brand Voice Generator
- **Purpose:** Rewrite in brand voice
- **Input:** `text: string`, `brand: string`
- **Output:** Text rewritten in brand tone
- **Access:** PUBLIC
- **Use Case:** Brand consistency, marketing copy

#### Q2 — Prompt Persona Stylist
- **Purpose:** Add persona to prompts
- **Input:** `prompt: string`, `persona: string`
- **Output:** Prompt with persona, vibe, personality
- **Access:** PUBLIC
- **Use Case:** Prompt engineering, personality design

#### Q3 — Author-Voice Converter
- **Purpose:** Imitate author style
- **Input:** `text: string`, `author: string`
- **Output:** Text in author's style
- **Access:** PUBLIC
- **Use Case:** Content creation, style emulation

#### Q4 — Narrative Cohesion Agent
- **Purpose:** Ensure consistency across outputs
- **Input:** `outputs: string[]`, `context: string (optional)`
- **Output:** Unified narrative with consistency notes
- **Access:** PUBLIC
- **Use Case:** Multi-chapter writing, story continuity

#### Q5 — Hook + CTA Generator
- **Purpose:** Create compelling hooks and calls-to-action
- **Input:** `content: string`, `platform: string (optional)`
- **Output:** Hook + CTA suggestions
- **Access:** PUBLIC
- **Use Case:** Marketing, social media, engagement

#### Q6 — Platform Localizer
- **Purpose:** Adapt to platform norms
- **Input:** `text: string`, `platform: string (Twitter, LinkedIn, Reddit, etc.)`
- **Output:** Text adapted for platform audience expectations
- **Access:** PUBLIC
- **Use Case:** Content distribution, platform-specific adaptation

#### Q7 — Audience Knowledge Level Tuner
- **Purpose:** Adjust for audience expertise
- **Input:** `text: string`, `audience_level: enum(beginner, intermediate, expert)`
- **Output:** Text rewritten for audience level
- **Access:** PUBLIC
- **Use Case:** Documentation, audience-specific content

---

### Section R: Strategy/Planning/Roadmaps (7 Skills) — **BDS ONLY**

#### R1 — Product Strategy Mapper
- **Purpose:** Map vision to priorities
- **Input:** `vision: string`, `timeframe: string`
- **Output:** Short-term + long-term priority mapping
- **Access:** BDS_ONLY
- **Use Case:** Strategic planning, product roadmapping

#### R2 — Capability Roadmap Builder
- **Purpose:** Build feature roadmap
- **Input:** `product: string`, `capabilities: string[]`
- **Output:** Roadmap with milestones, dependencies, phases
- **Access:** BDS_ONLY
- **Use Case:** Product planning, timeline estimation

#### R3 — Risk Forecast Agent
- **Purpose:** Forecast risks
- **Input:** `plan: string`, `context: string (optional)`
- **Output:** Risk forecast (operational, financial, technical)
- **Access:** BDS_ONLY
- **Use Case:** Risk management, contingency planning

#### R4 — Pricing Strategy Planner
- **Purpose:** Design pricing model
- **Input:** `product: string`, `market: string (optional)`
- **Output:** Pricing strategies with comparison (premium, tiered, enterprise)
- **Access:** BDS_ONLY
- **Use Case:** Business model, monetization

#### R5 — Partner Channel Advisor
- **Purpose:** Identify partnership opportunities
- **Input:** `product: string`, `market: string`
- **Output:** Partnership channel recommendations
- **Access:** BDS_ONLY
- **Use Case:** Go-to-market, channel strategy

#### R6 — Competitive Moat Evaluator
- **Purpose:** Assess competitive advantage
- **Input:** `product: string`, `market: string (optional)`
- **Output:** Moat analysis + differentiation strategy
- **Access:** BDS_ONLY
- **Use Case:** Competitive positioning, strategy

#### R7 — Go-To-Market Planner
- **Purpose:** Plan market launch
- **Input:** `product: string`, `launch_date: string (optional)`
- **Output:** GTM plan (audience, channels, positioning, KPIs)
- **Access:** BDS_ONLY
- **Use Case:** Launch planning, market entry

---

### Section S: Forge Ecosystem Orchestration (9 Skills) — **BDS ONLY**

#### S1 — Forge Interop Planner
- **Purpose:** Plan cross-product interactions
- **Input:** `feature: string`, `products: string[] (VibeForge, AuthorForge, DataForge, etc.)`
- **Output:** Integration plan across Forge ecosystem
- **Access:** BDS_ONLY
- **Use Case:** Ecosystem feature design

#### S2 — Cross-Product Identity Agent
- **Purpose:** Ensure consistent identity
- **Input:** `element: string`, `products: string[]`
- **Output:** Consistency guidelines across products
- **Access:** BDS_ONLY
- **Use Case:** Brand consistency, design system

#### S3 — Forge-Wide Feature Proposal
- **Purpose:** Propose ecosystem features
- **Input:** `feature_idea: string`, `benefit: string`
- **Output:** Cross-product feature proposal with shared components
- **Access:** BDS_ONLY
- **Use Case:** Ecosystem innovation, platform thinking

#### S4 — Ecosystem Memory Strategy
- **Purpose:** Plan shared knowledge
- **Input:** `use_cases: string[]`
- **Output:** Shared memory + knowledge UX strategy across products
- **Access:** BDS_ONLY
- **Use Case:** Knowledge management, ecosystem coherence

#### S5 — Ecosystem Scaling Agent
- **Purpose:** Plan scaling across products
- **Input:** `growth_targets: string`, `products: string[]`
- **Output:** Scaling strategy for multi-product ecosystem
- **Access:** BDS_ONLY
- **Use Case:** Infrastructure planning, scalability

#### S6 — Forge Operational Standards
- **Purpose:** Define ecosystem standards
- **Input:** `areas: string[] (deployment, security, performance, etc.)`
- **Output:** SAS-aligned operational standards for all apps
- **Access:** BDS_ONLY
- **Use Case:** Governance, SAS compliance

#### S7 — Ecosystem Impact Analyst
- **Purpose:** Analyze system-wide effects
- **Input:** `change: string`, `affected_products: string[]`
- **Output:** Ecosystem-level impact analysis
- **Access:** BDS_ONLY
- **Use Case:** Change management, risk assessment

#### S8 — Product-Fusion Design Agent
- **Purpose:** Merge product concepts
- **Input:** `product_a: string`, `product_b: string`
- **Output:** Unified concept with shared components
- **Access:** BDS_ONLY
- **Use Case:** Product strategy, consolidation

#### S9 — Forge Brand Evolution
- **Purpose:** Plan brand growth
- **Input:** `current_positioning: string`, `market_trends: string (optional)`
- **Output:** Future brand directions + evolution strategy
- **Access:** BDS_ONLY
- **Use Case:** Brand strategy, long-term positioning

---

## Access Control Rules

**PUBLIC Skills (45 total):**
- Accessible via `/api/v1/skills/{skillId}`
- VibeForge frontend can call these
- No authentication required (anonymous OK)
- Rate limited to 100/min per IP

**BDS_ONLY Skills (75 total):**
- Accessible via `/api/v1/bds/skills/{skillId}`
- Requires BDS authentication token
- VibeForge_BDS frontend only
- Rate limited per authenticated user

**Access Check Implementation:**
```
GET /api/v1/skills/{skillId}
  → Return 200 if PUBLIC
  → Return 404 if BDS_ONLY (hide from public)

GET /api/v1/bds/skills/{skillId}
  → Validate BDS token
  → Return 200 if authorized
  → Return 401 if not authenticated
  → Return 403 if not BDS user
```

---

## API Contract Template

All skills follow this REST pattern:

```typescript
POST /api/v1/skills/{skillId}/invoke

Request:
{
  "inputs": {
    "param1": "value1",
    "param2": "value2"
  },
  "options": {
    "model": "claude-3.5-sonnet" (optional),
    "temperature": 0.7 (optional),
    "max_tokens": 2000 (optional)
  }
}

Response:
{
  "sessionId": "sk_123456",
  "status": "success" | "error",
  "output": "...",
  "metadata": {
    "tokens_used": 1234,
    "cost": 0.0045,
    "latency_ms": 2345,
    "model_used": "claude-3.5-sonnet"
  }
}

Streaming:
POST /api/v1/skills/{skillId}/invoke?stream=true
  → Returns Server-Sent Events stream
  → Tokens streamed real-time
```

---

## Skills Discovery

**List all PUBLIC skills:**
```
GET /api/v1/skills
  → Returns [45 PUBLIC skills with metadata]
```

**List all BDS skills (authenticated only):**
```
GET /api/v1/bds/skills
  → Returns [120 total skills]
```

**Search skills:**
```
GET /api/v1/skills/search?query=prompt
  → Returns matching PUBLIC skills
```

---

## Implementation Status

**Phase 1:** All 120 skills defined (backend API spec) ✅
**Phase 2:** VibeForge (public) integration (45 skills) → In progress
**Phase 3:** VibeForge_BDS integration (120 skills) → Planned

---

**Version:** 1.0  
**Last Updated:** December 8, 2025  
**Maintained by:** Boswell Digital Solutions LLC
