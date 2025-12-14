# VibeForge Phase 2: Architecture Specification

**Version:** 2.0  
**Date:** December 6, 2025  
**Status:** Implementation-Ready  

This document addresses all gaps identified in the architectural review, providing interfaces, specifications, schemas, protocols, and task flows.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Agent Specification](#2-agent-specification)
3. [API Boundary Specification](#3-api-boundary-specification)
4. [License Management System](#4-license-management-system)
5. [Model Routing Interface (NeuroForge)](#5-model-routing-interface-neuroforge)
6. [Planning Orchestration](#6-planning-orchestration)
7. [Monitoring & Observability](#7-monitoring--observability)
8. [Security Posture](#8-security-posture)
9. [Failure Modes & Recovery](#9-failure-modes--recovery)

---

## 1. System Architecture Overview

### 1.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  VibeForge  │  │ AuthorForge │  │ TradeForge  │  │   Web App   │    │
│  │  (Desktop)  │  │  (Desktop)  │  │  (Desktop)  │  │  (Browser)  │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │
└─────────┼────────────────┼────────────────┼────────────────┼───────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Kong / Traefik / Custom Gateway                                 │   │
│  │  - Rate Limiting    - Auth Verification    - Request Routing     │   │
│  │  - SSL Termination  - API Versioning       - Load Balancing      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ForgeAgents   │    │   NeuroForge    │    │   DataForge     │
│     :8002       │    │     :8000       │    │     :8001       │
│                 │    │                 │    │                 │
│ - Agent Mgmt    │◄──►│ - LLM Routing   │◄──►│ - PostgreSQL    │
│ - Task Queue    │    │ - Multi-Model   │    │ - pgvector      │
│ - Licensing     │    │ - Streaming     │    │ - Redis Cache   │
│ - Orchestration │    │ - Cost Tracking │    │ - Audit Logs    │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  RabbitMQ    │  │   Cortex     │  │    Rake      │  │  Temporal  │  │
│  │  (Messages)  │  │ (Filesystem) │  │  (Ingestion) │  │ (Workflow) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow Diagram

```
┌──────────┐     1. Request      ┌─────────────┐
│VibeForge │ ─────────────────► │ ForgeAgents │
│ Desktop  │                     │   (API)     │
└────┬─────┘                     └──────┬──────┘
     │                                  │
     │                           2. Verify License
     │                                  │
     │                                  ▼
     │                          ┌──────────────┐
     │                          │  DataForge   │
     │                          │ (License DB) │
     │                          └──────┬───────┘
     │                                 │
     │                          3. Create Agent
     │                                 │
     │                                 ▼
     │                          ┌──────────────┐
     │      6. SSE Events       │    Agent     │
     │ ◄─────────────────────── │   Runner     │
     │                          └──────┬───────┘
     │                                 │
     │                          4. Call LLM
     │                                 │
     │                                 ▼
     │                          ┌──────────────┐
     │                          │  NeuroForge  │
     │                          │ (LLM Router) │
     │                          └──────┬───────┘
     │                                 │
     │                          5. Store Results
     │                                 │
     │                                 ▼
     │                          ┌──────────────┐
     │                          │  DataForge   │
     │                          │  (Results)   │
     └─────────────────────────►└──────────────┘
                 7. Fetch Results
```

---

## 2. Agent Specification

### 2.1 Agent Schema

```typescript
// Core Agent Types
interface Agent {
  // Identity
  id: string;                    // UUID v4
  name: string;                  // Human-readable name
  type: AgentType;
  version: string;               // Semantic version
  
  // Ownership
  userId: string;
  organizationId?: string;
  applicationId: string;         // vibeforge | authorforge | tradeforge
  
  // State
  status: AgentStatus;
  createdAt: Date;
  updatedAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  
  // Configuration
  config: AgentConfig;
  policy: AgentPolicy;
  
  // Runtime
  memory: AgentMemory;
  tasks: Task[];
  currentTaskId?: string;
  
  // Results
  outputs: AgentOutput[];
  error?: AgentError;
  
  // Metrics
  metrics: AgentMetrics;
}

type AgentType = 
  | 'planner'       // Multi-stage planning (Cortex)
  | 'executor'      // Single task execution
  | 'evaluator'     // Quality assessment
  | 'coordinator'   // Orchestrates other agents
  | 'researcher'    // Web search + synthesis
  | 'coder'         // Code generation/modification
  | 'reviewer'      // Code review
  | 'custom';       // User-defined

type AgentStatus =
  | 'created'       // Agent created, not started
  | 'queued'        // Waiting for resources
  | 'initializing'  // Loading context, verifying permissions
  | 'running'       // Actively executing
  | 'paused'        // User-paused
  | 'waiting'       // Waiting for user input
  | 'completed'     // Successfully finished
  | 'failed'        // Encountered unrecoverable error
  | 'cancelled'     // User cancelled
  | 'expired';      // Timed out

interface AgentConfig {
  // Execution
  maxDurationSeconds: number;    // Default: 3600 (1 hour)
  maxRetries: number;            // Default: 3
  retryDelayMs: number;          // Default: 1000
  
  // Resources
  maxTokens: number;             // Token budget
  maxCost: number;               // Cost limit in USD
  priority: 'low' | 'normal' | 'high';
  
  // Behavior
  streamOutput: boolean;         // Enable SSE streaming
  persistMemory: boolean;        // Save memory after completion
  allowParallelTasks: boolean;
  
  // Model preferences
  preferredProvider?: string;    // openai | anthropic | xai | google
  preferredModel?: string;
  temperature?: number;
}

interface AgentPolicy {
  // Permissions
  allowLLMCalls: boolean;
  allowFilesystemAccess: boolean;
  allowNetworkAccess: boolean;
  allowCodeExecution: boolean;
  allowDatabaseAccess: boolean;
  
  // Restrictions
  allowedDomains?: string[];     // Network whitelist
  allowedPaths?: string[];       // Filesystem whitelist
  blockedTools?: string[];       // Disabled capabilities
  
  // Data handling
  dataRetentionDays: number;
  allowPII: boolean;
  encryptOutputs: boolean;
  
  // Audit
  logAllCalls: boolean;
  requireApprovalFor?: string[]; // Actions needing human approval
}
```

### 2.2 Agent Memory Schema

```typescript
interface AgentMemory {
  // Short-term (current session)
  shortTerm: {
    conversationHistory: Message[];
    workingContext: string;
    recentTools: ToolResult[];
    scratchpad: Record<string, unknown>;
  };
  
  // Long-term (persisted)
  longTerm: {
    learnedPatterns: Pattern[];
    userPreferences: Preference[];
    domainKnowledge: KnowledgeItem[];
    pastDecisions: Decision[];
  };
  
  // Episodic (task-specific)
  episodic: {
    taskId: string;
    stepHistory: ExecutionStep[];
    checkpoints: Checkpoint[];
  };
  
  // Semantic (RAG)
  semantic: {
    vectorStoreId?: string;
    embeddingModel: string;
    retrievalConfig: RetrievalConfig;
  };
}

interface Message {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: Date;
  tokenCount: number;
  metadata?: Record<string, unknown>;
}

interface Checkpoint {
  id: string;
  taskId: string;
  stepIndex: number;
  state: Record<string, unknown>;
  createdAt: Date;
  canResume: boolean;
}
```

### 2.3 Task Schema

```typescript
interface Task {
  id: string;
  agentId: string;
  parentTaskId?: string;         // For subtasks
  
  // Definition
  type: TaskType;
  name: string;
  description: string;
  input: TaskInput;
  
  // Execution
  status: TaskStatus;
  attempts: number;
  currentStep: number;
  totalSteps: number;
  
  // Timing
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  estimatedDuration?: number;
  
  // Results
  output?: TaskOutput;
  error?: TaskError;
  
  // Dependencies
  dependsOn?: string[];          // Task IDs that must complete first
  blockedBy?: string[];          // Currently blocking task IDs
}

type TaskType =
  | 'llm_call'
  | 'tool_execution'
  | 'human_review'
  | 'file_operation'
  | 'api_call'
  | 'code_execution'
  | 'composite';                 // Multi-step task

type TaskStatus =
  | 'pending'
  | 'blocked'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'skipped';

interface TaskInput {
  prompt?: string;
  context?: string;
  files?: FileReference[];
  parameters?: Record<string, unknown>;
  tools?: string[];
}

interface TaskOutput {
  result: unknown;
  artifacts?: Artifact[];
  tokensUsed: number;
  cost: number;
  duration: number;
}

interface Artifact {
  id: string;
  type: 'text' | 'code' | 'file' | 'image' | 'structured';
  name: string;
  content: string | Buffer;
  mimeType: string;
  size: number;
}
```

### 2.4 Agent Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AGENT LIFECYCLE                                   │
└─────────────────────────────────────────────────────────────────────────┘

     ┌──────────┐
     │  CREATE  │ ─────► POST /agents
     └────┬─────┘         - Validate request
          │               - Check license/quota
          ▼               - Create agent record
     ┌──────────┐
     │  QUEUED  │ ─────► Agent waits for worker
     └────┬─────┘         - Priority queue
          │               - Resource availability
          ▼
     ┌──────────┐
     │   INIT   │ ─────► Worker picks up agent
     └────┬─────┘         - Load memory
          │               - Initialize tools
          │               - Verify permissions
          ▼
     ┌──────────┐         ┌──────────┐
     │ RUNNING  │◄───────►│  PAUSED  │
     └────┬─────┘         └──────────┘
          │    User pause/resume
          │
          │  ┌─────────────────────────────────────┐
          │  │          TASK EXECUTION             │
          │  │                                     │
          │  │  ┌──────┐  ┌──────┐  ┌──────────┐  │
          │  │  │ Plan │─►│ Run  │─►│ Evaluate │  │
          │  │  └──────┘  └──────┘  └──────────┘  │
          │  │       │         │          │       │
          │  │       ▼         ▼          ▼       │
          │  │    SSE Event  SSE Event  SSE Event │
          │  └─────────────────────────────────────┘
          │
          ├──────────────┬──────────────┐
          ▼              ▼              ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │COMPLETED │  │  FAILED  │  │CANCELLED │
     └────┬─────┘  └────┬─────┘  └────┬─────┘
          │             │             │
          └─────────────┴─────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   CLEANUP    │
                 │ - Save memory│
                 │ - Store logs │
                 │ - Free resources
                 └──────────────┘
```

---

## 3. API Boundary Specification

### 3.1 ForgeAgents REST API

```yaml
openapi: 3.0.3
info:
  title: ForgeAgents API
  version: 1.0.0
  description: Agent orchestration and execution API

servers:
  - url: http://localhost:8002/api/v1
    description: Development
  - url: https://api.forge.ai/agents/v1
    description: Production

security:
  - BearerAuth: []
  - ApiKeyAuth: []

paths:
  # ═══════════════════════════════════════════════════
  # AUTHENTICATION
  # ═══════════════════════════════════════════════════
  
  /auth/login:
    post:
      summary: Authenticate user
      tags: [Authentication]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email: { type: string, format: email }
                password: { type: string, minLength: 8 }
                deviceId: { type: string }
                applicationId: { type: string, enum: [vibeforge, authorforge, tradeforge] }
      responses:
        200:
          description: Authentication successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'
        401:
          $ref: '#/components/responses/Unauthorized'

  /auth/refresh:
    post:
      summary: Refresh access token
      tags: [Authentication]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [refresh_token]
              properties:
                refresh_token: { type: string }
      responses:
        200:
          description: Token refreshed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AuthResponse'

  /auth/logout:
    post:
      summary: Invalidate session
      tags: [Authentication]
      responses:
        204:
          description: Logged out successfully

  # ═══════════════════════════════════════════════════
  # LICENSE MANAGEMENT
  # ═══════════════════════════════════════════════════
  
  /license:
    get:
      summary: Get current license
      tags: [License]
      responses:
        200:
          description: License details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/License'

  /license/verify:
    post:
      summary: Verify license for feature
      tags: [License]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [feature]
              properties:
                feature: { type: string }
                deviceId: { type: string }
      responses:
        200:
          description: Verification result
          content:
            application/json:
              schema:
                type: object
                properties:
                  allowed: { type: boolean }
                  reason: { type: string }
                  upgradeUrl: { type: string }

  /license/usage:
    get:
      summary: Get usage for current period
      tags: [License]
      responses:
        200:
          description: Usage details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UsageReport'

  # ═══════════════════════════════════════════════════
  # AGENT MANAGEMENT
  # ═══════════════════════════════════════════════════
  
  /agents:
    get:
      summary: List agents
      tags: [Agents]
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [running, completed, failed, all]
        - name: type
          in: query
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
      responses:
        200:
          description: List of agents
          content:
            application/json:
              schema:
                type: object
                properties:
                  agents:
                    type: array
                    items:
                      $ref: '#/components/schemas/AgentSummary'
                  total: { type: integer }
                  hasMore: { type: boolean }

    post:
      summary: Create new agent
      tags: [Agents]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateAgentRequest'
      responses:
        201:
          description: Agent created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Agent'
        400:
          $ref: '#/components/responses/BadRequest'
        402:
          $ref: '#/components/responses/PaymentRequired'
        429:
          $ref: '#/components/responses/RateLimited'

  /agents/{agentId}:
    get:
      summary: Get agent details
      tags: [Agents]
      parameters:
        - $ref: '#/components/parameters/agentId'
      responses:
        200:
          description: Agent details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Agent'
        404:
          $ref: '#/components/responses/NotFound'

    delete:
      summary: Cancel and delete agent
      tags: [Agents]
      parameters:
        - $ref: '#/components/parameters/agentId'
      responses:
        204:
          description: Agent deleted

  /agents/{agentId}/start:
    post:
      summary: Start agent execution
      tags: [Agents]
      parameters:
        - $ref: '#/components/parameters/agentId'
      responses:
        200:
          description: Agent started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Agent'

  /agents/{agentId}/pause:
    post:
      summary: Pause agent execution
      tags: [Agents]
      parameters:
        - $ref: '#/components/parameters/agentId'
      responses:
        200:
          description: Agent paused

  /agents/{agentId}/resume:
    post:
      summary: Resume paused agent
      tags: [Agents]
      parameters:
        - $ref: '#/components/parameters/agentId'
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                additionalContext: { type: string }
      responses:
        200:
          description: Agent resumed

  /agents/{agentId}/cancel:
    post:
      summary: Cancel agent execution
      tags: [Agents]
      parameters:
        - $ref: '#/components/parameters/agentId'
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                reason: { type: string }
      responses:
        200:
          description: Agent cancelled

  # ═══════════════════════════════════════════════════
  # AGENT EVENTS (SSE)
  # ═══════════════════════════════════════════════════
  
  /agents/{agentId}/events:
    get:
      summary: Stream agent events (SSE)
      tags: [Agents]
      parameters:
        - $ref: '#/components/parameters/agentId'
        - name: lastEventId
          in: query
          description: Resume from specific event
          schema:
            type: string
      responses:
        200:
          description: SSE event stream
          content:
            text/event-stream:
              schema:
                type: string
                example: |
                  event: status_changed
                  data: {"status": "running", "timestamp": "2025-12-06T10:30:00Z"}
                  
                  event: task_started
                  data: {"taskId": "task-123", "type": "llm_call"}
                  
                  event: output_chunk
                  data: {"content": "Here is the ", "taskId": "task-123"}

  # ═══════════════════════════════════════════════════
  # TASKS
  # ═══════════════════════════════════════════════════
  
  /agents/{agentId}/tasks:
    get:
      summary: List agent tasks
      tags: [Tasks]
      parameters:
        - $ref: '#/components/parameters/agentId'
      responses:
        200:
          description: List of tasks
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Task'

    post:
      summary: Add task to agent
      tags: [Tasks]
      parameters:
        - $ref: '#/components/parameters/agentId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTaskRequest'
      responses:
        201:
          description: Task created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'

  /agents/{agentId}/tasks/{taskId}:
    get:
      summary: Get task details
      tags: [Tasks]
      parameters:
        - $ref: '#/components/parameters/agentId'
        - $ref: '#/components/parameters/taskId'
      responses:
        200:
          description: Task details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'

  /agents/{agentId}/tasks/{taskId}/output:
    get:
      summary: Get task output
      tags: [Tasks]
      parameters:
        - $ref: '#/components/parameters/agentId'
        - $ref: '#/components/parameters/taskId'
      responses:
        200:
          description: Task output
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskOutput'

  # ═══════════════════════════════════════════════════
  # CORTEX (PLANNING)
  # ═══════════════════════════════════════════════════
  
  /cortex/sessions:
    post:
      summary: Start planning session
      tags: [Cortex]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreatePlanningSessionRequest'
      responses:
        201:
          description: Session created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PlanningSession'

  /cortex/sessions/stream:
    post:
      summary: Start planning session with SSE streaming
      tags: [Cortex]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreatePlanningSessionRequest'
      responses:
        200:
          description: SSE event stream
          content:
            text/event-stream:
              schema:
                type: string

  /cortex/sessions/{sessionId}:
    get:
      summary: Get planning session
      tags: [Cortex]
      parameters:
        - $ref: '#/components/parameters/sessionId'
      responses:
        200:
          description: Session details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PlanningSession'

  /cortex/sessions/{sessionId}/deliverable:
    get:
      summary: Get final deliverable
      tags: [Cortex]
      parameters:
        - $ref: '#/components/parameters/sessionId'
      responses:
        200:
          description: Two-file deliverable
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TwoFileDeliverable'

  /cortex/pipelines:
    get:
      summary: List available pipelines
      tags: [Cortex]
      responses:
        200:
          description: Pipeline list
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Pipeline'

  /cortex/estimate:
    post:
      summary: Estimate planning cost
      tags: [Cortex]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreatePlanningSessionRequest'
      responses:
        200:
          description: Cost estimate
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CostEstimate'

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  parameters:
    agentId:
      name: agentId
      in: path
      required: true
      schema:
        type: string
        format: uuid
    taskId:
      name: taskId
      in: path
      required: true
      schema:
        type: string
        format: uuid
    sessionId:
      name: sessionId
      in: path
      required: true
      schema:
        type: string
        format: uuid

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    PaymentRequired:
      description: License or quota exceeded
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    RateLimited:
      description: Too many requests
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          headers:
            X-RateLimit-Limit:
              schema: { type: integer }
            X-RateLimit-Remaining:
              schema: { type: integer }
            X-RateLimit-Reset:
              schema: { type: integer }

  schemas:
    Error:
      type: object
      required: [code, message]
      properties:
        code: { type: string }
        message: { type: string }
        details: { type: object }
        requestId: { type: string }

    AuthResponse:
      type: object
      properties:
        access_token: { type: string }
        refresh_token: { type: string }
        expires_at: { type: string, format: date-time }
        user:
          type: object
          properties:
            id: { type: string }
            email: { type: string }
            displayName: { type: string }

    License:
      type: object
      properties:
        id: { type: string }
        tier: { type: string, enum: [free, trial, pro, enterprise] }
        status: { type: string, enum: [active, expired, cancelled] }
        features: { type: array, items: { type: string } }
        limits:
          type: object
          additionalProperties: { type: integer }
        trialEndsAt: { type: string, format: date-time }
        subscriptionEndsAt: { type: string, format: date-time }

    UsageReport:
      type: object
      properties:
        periodStart: { type: string, format: date-time }
        periodEnd: { type: string, format: date-time }
        usage:
          type: object
          additionalProperties:
            type: object
            properties:
              used: { type: integer }
              limit: { type: integer }
              remaining: { type: integer }

    CreateAgentRequest:
      type: object
      required: [type, name]
      properties:
        type: { type: string }
        name: { type: string }
        description: { type: string }
        config:
          type: object
          properties:
            maxDurationSeconds: { type: integer, default: 3600 }
            maxTokens: { type: integer }
            maxCost: { type: number }
            priority: { type: string, enum: [low, normal, high] }
            streamOutput: { type: boolean, default: true }
        policy:
          type: object
          properties:
            allowLLMCalls: { type: boolean, default: true }
            allowFilesystemAccess: { type: boolean, default: false }
            allowNetworkAccess: { type: boolean, default: false }
        initialContext: { type: string }
        initialTasks:
          type: array
          items:
            $ref: '#/components/schemas/CreateTaskRequest'

    Agent:
      type: object
      properties:
        id: { type: string, format: uuid }
        type: { type: string }
        name: { type: string }
        status: { type: string }
        createdAt: { type: string, format: date-time }
        startedAt: { type: string, format: date-time }
        completedAt: { type: string, format: date-time }
        config: { type: object }
        policy: { type: object }
        currentTaskId: { type: string }
        metrics:
          type: object
          properties:
            tasksCompleted: { type: integer }
            tasksFailed: { type: integer }
            tokensUsed: { type: integer }
            cost: { type: number }
            duration: { type: integer }

    AgentSummary:
      type: object
      properties:
        id: { type: string }
        type: { type: string }
        name: { type: string }
        status: { type: string }
        createdAt: { type: string, format: date-time }
        progress: { type: number }

    CreateTaskRequest:
      type: object
      required: [type, name]
      properties:
        type: { type: string }
        name: { type: string }
        description: { type: string }
        input:
          type: object
          properties:
            prompt: { type: string }
            context: { type: string }
            parameters: { type: object }
        dependsOn:
          type: array
          items: { type: string }

    Task:
      type: object
      properties:
        id: { type: string }
        agentId: { type: string }
        type: { type: string }
        name: { type: string }
        status: { type: string }
        attempts: { type: integer }
        currentStep: { type: integer }
        totalSteps: { type: integer }
        createdAt: { type: string, format: date-time }
        startedAt: { type: string, format: date-time }
        completedAt: { type: string, format: date-time }

    TaskOutput:
      type: object
      properties:
        result: { type: object }
        artifacts:
          type: array
          items:
            type: object
            properties:
              id: { type: string }
              type: { type: string }
              name: { type: string }
              mimeType: { type: string }
              size: { type: integer }
              url: { type: string }
        tokensUsed: { type: integer }
        cost: { type: number }
        duration: { type: integer }

    CreatePlanningSessionRequest:
      type: object
      required: [title, description]
      properties:
        title: { type: string, minLength: 1, maxLength: 200 }
        description: { type: string, minLength: 10, maxLength: 10000 }
        context: { type: string, maxLength: 50000 }
        pipeline: { type: string, enum: [default, quick, deep], default: default }
        pauseAfterReview: { type: boolean, default: false }
        requireTestCoverage: { type: boolean, default: true }
        targetCoverage: { type: integer, minimum: 0, maximum: 100, default: 100 }

    PlanningSession:
      type: object
      properties:
        id: { type: string }
        status: { type: string }
        pipeline: { type: string }
        createdAt: { type: string, format: date-time }
        stages:
          type: array
          items:
            type: object
            properties:
              index: { type: integer }
              type: { type: string }
              provider: { type: string }
              model: { type: string }
              status: { type: string }
              durationMs: { type: integer }
              tokensUsed: { type: integer }
              cost: { type: number }
        currentStageIndex: { type: integer }
        totalTokens: { type: integer }
        totalCost: { type: number }

    TwoFileDeliverable:
      type: object
      properties:
        implementationPlan:
          type: object
          properties:
            content: { type: string }
            filename: { type: string }
            sections: { type: array, items: { type: string } }
        claudeCodePrompt:
          type: object
          properties:
            content: { type: string }
            filename: { type: string }
            phases: { type: integer }
            estimatedTime: { type: string }
        parseWarnings:
          type: array
          items: { type: string }

    Pipeline:
      type: object
      properties:
        name: { type: string }
        description: { type: string }
        stagesCount: { type: integer }
        stages:
          type: array
          items:
            type: object
            properties:
              type: { type: string }
              provider: { type: string }
              model: { type: string }

    CostEstimate:
      type: object
      properties:
        pipeline: { type: string }
        estimatedInputTokens: { type: integer }
        estimatedOutputTokens: { type: integer }
        estimatedCostMin: { type: number }
        estimatedCostMax: { type: number }
```

### 3.2 SSE Event Types

```typescript
// All SSE events follow this structure
interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
  id?: string;                   // For resume capability
  retry?: number;                // Reconnection delay in ms
}

type SSEEventType =
  // Agent lifecycle
  | 'agent_created'
  | 'agent_started'
  | 'agent_paused'
  | 'agent_resumed'
  | 'agent_completed'
  | 'agent_failed'
  | 'agent_cancelled'
  
  // Task lifecycle
  | 'task_queued'
  | 'task_started'
  | 'task_progress'
  | 'task_completed'
  | 'task_failed'
  
  // Output streaming
  | 'output_chunk'               // Streaming LLM output
  | 'output_complete'
  
  // Planning specific
  | 'stage_started'
  | 'stage_progress'
  | 'stage_completed'
  | 'stage_failed'
  | 'session_completed'
  | 'session_failed'
  
  // System
  | 'heartbeat'
  | 'error'
  | 'reconnect';

// Example event payloads
interface OutputChunkEvent {
  event: 'output_chunk';
  data: {
    taskId: string;
    content: string;
    index: number;
  };
}

interface TaskCompletedEvent {
  event: 'task_completed';
  data: {
    taskId: string;
    output: TaskOutput;
    nextTaskId?: string;
  };
}

interface StageProgressEvent {
  event: 'stage_progress';
  data: {
    sessionId: string;
    stageIndex: number;
    token: string;
  };
}
```

### 3.3 Error Codes

```typescript
const ERROR_CODES = {
  // Authentication (1xxx)
  AUTH_REQUIRED: 'E1001',
  INVALID_TOKEN: 'E1002',
  TOKEN_EXPIRED: 'E1003',
  INVALID_CREDENTIALS: 'E1004',
  
  // Authorization (2xxx)
  FORBIDDEN: 'E2001',
  INSUFFICIENT_PERMISSIONS: 'E2002',
  FEATURE_NOT_AVAILABLE: 'E2003',
  
  // License (3xxx)
  LICENSE_EXPIRED: 'E3001',
  QUOTA_EXCEEDED: 'E3002',
  FEATURE_REQUIRES_UPGRADE: 'E3003',
  DEVICE_LIMIT_REACHED: 'E3004',
  
  // Validation (4xxx)
  INVALID_REQUEST: 'E4001',
  MISSING_REQUIRED_FIELD: 'E4002',
  INVALID_FIELD_VALUE: 'E4003',
  PAYLOAD_TOO_LARGE: 'E4004',
  
  // Resource (5xxx)
  NOT_FOUND: 'E5001',
  ALREADY_EXISTS: 'E5002',
  CONFLICT: 'E5003',
  GONE: 'E5004',
  
  // Agent (6xxx)
  AGENT_NOT_RUNNING: 'E6001',
  AGENT_ALREADY_RUNNING: 'E6002',
  AGENT_CANCELLED: 'E6003',
  AGENT_FAILED: 'E6004',
  INVALID_AGENT_STATE: 'E6005',
  
  // Task (7xxx)
  TASK_NOT_FOUND: 'E7001',
  TASK_ALREADY_COMPLETED: 'E7002',
  TASK_DEPENDENCY_FAILED: 'E7003',
  
  // External (8xxx)
  LLM_ERROR: 'E8001',
  LLM_RATE_LIMIT: 'E8002',
  LLM_TIMEOUT: 'E8003',
  EXTERNAL_SERVICE_ERROR: 'E8004',
  
  // System (9xxx)
  INTERNAL_ERROR: 'E9001',
  SERVICE_UNAVAILABLE: 'E9002',
  RATE_LIMITED: 'E9003',
  MAINTENANCE_MODE: 'E9004',
};
```

---

## 4. License Management System

### 4.1 License Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LICENSE VERIFICATION FLOW                         │
└─────────────────────────────────────────────────────────────────────────┘

  DESKTOP APP                    FORGEAGENTS                   DATAFORGE
       │                              │                            │
       │  1. Request Feature          │                            │
       │ ────────────────────────────►│                            │
       │  (JWT + deviceId + feature)  │                            │
       │                              │                            │
       │                              │  2. Check Cache            │
       │                              │ ◄─────────────────         │
       │                              │                            │
       │                     [Cache Miss]                          │
       │                              │                            │
       │                              │  3. Query License          │
       │                              │ ──────────────────────────►│
       │                              │                            │
       │                              │  4. License + Limits       │
       │                              │ ◄──────────────────────────│
       │                              │                            │
       │                              │  5. Verify:                │
       │                              │  - Tier allows feature     │
       │                              │  - Quota not exceeded      │
       │                              │  - Device authorized       │
       │                              │  - Not expired             │
       │                              │                            │
       │  6. Response                 │                            │
       │ ◄────────────────────────────│                            │
       │  { allowed, reason, quota }  │                            │
       │                              │                            │
      [If Allowed]                    │                            │
       │                              │                            │
       │  7. Execute Feature          │                            │
       │ ────────────────────────────►│                            │
       │                              │                            │
       │                              │  8. Track Usage            │
       │                              │ ──────────────────────────►│
       │                              │                            │
```

### 4.2 License Schema

```typescript
interface License {
  id: string;
  userId: string;
  organizationId?: string;
  
  // Tier & Status
  tier: 'free' | 'trial' | 'pro' | 'enterprise';
  status: 'active' | 'expired' | 'cancelled' | 'suspended';
  
  // Validity
  createdAt: Date;
  activatedAt?: Date;
  expiresAt?: Date;
  trialEndsAt?: Date;
  
  // Features
  features: string[];
  limits: LicenseLimits;
  
  // Devices
  devices: LicenseDevice[];
  maxDevices: number;
  
  // Billing
  stripeCustomerId?: string;
  stripeSubscriptionId?: string;
  
  // Metadata
  source: 'signup' | 'upgrade' | 'coupon' | 'enterprise' | 'lifetime';
  couponCode?: string;
  notes?: string;
}

interface LicenseLimits {
  // Agents
  maxConcurrentAgents: number;
  maxAgentsPerDay: number;
  maxAgentDurationSeconds: number;
  
  // Planning
  planningSessionsPerMonth: number;
  modelsPerSession: number;
  maxContextTokens: number;
  
  // Storage
  maxStorageBytes: number;
  promptLibrarySize: number;
  
  // Team
  teamMembers: number;
  
  // API
  apiRequestsPerMinute: number;
  apiRequestsPerDay: number;
}

interface LicenseDevice {
  id: string;
  name: string;
  platform: 'windows' | 'macos' | 'linux';
  fingerprint: string;
  firstSeenAt: Date;
  lastSeenAt: Date;
  isActive: boolean;
}

// Feature flags
const FEATURES = {
  // Core
  BASIC_AGENTS: 'agents.basic',
  ADVANCED_AGENTS: 'agents.advanced',
  CUSTOM_AGENTS: 'agents.custom',
  
  // Cortex
  CORTEX_BASIC: 'cortex.basic',
  CORTEX_MULTI_AI: 'cortex.multi_ai',
  CORTEX_CUSTOM_MODELS: 'cortex.custom_models',
  
  // Tools
  PROMPT_LIBRARY: 'tools.prompt_library',
  CONTEXT_BLOCKS: 'tools.context_blocks',
  CODE_EXECUTION: 'tools.code_execution',
  
  // Collaboration
  TEAM_SHARING: 'collab.team_sharing',
  REAL_TIME_COLLAB: 'collab.real_time',
  
  // Support
  PRIORITY_SUPPORT: 'support.priority',
  API_ACCESS: 'api.access',
  WEBHOOKS: 'api.webhooks',
} as const;

// Tier configurations
const TIER_CONFIG: Record<string, { features: string[], limits: Partial<LicenseLimits> }> = {
  free: {
    features: [FEATURES.BASIC_AGENTS, FEATURES.CORTEX_BASIC],
    limits: {
      maxConcurrentAgents: 1,
      maxAgentsPerDay: 5,
      planningSessionsPerMonth: 5,
      maxContextTokens: 8000,
      promptLibrarySize: 10,
      teamMembers: 1,
    },
  },
  trial: {
    features: [
      FEATURES.BASIC_AGENTS,
      FEATURES.ADVANCED_AGENTS,
      FEATURES.CORTEX_BASIC,
      FEATURES.CORTEX_MULTI_AI,
      FEATURES.PROMPT_LIBRARY,
      FEATURES.CONTEXT_BLOCKS,
    ],
    limits: {
      maxConcurrentAgents: 3,
      maxAgentsPerDay: 50,
      planningSessionsPerMonth: 50,
      maxContextTokens: 32000,
      promptLibrarySize: 100,
      teamMembers: 3,
    },
  },
  pro: {
    features: [
      FEATURES.BASIC_AGENTS,
      FEATURES.ADVANCED_AGENTS,
      FEATURES.CUSTOM_AGENTS,
      FEATURES.CORTEX_BASIC,
      FEATURES.CORTEX_MULTI_AI,
      FEATURES.CORTEX_CUSTOM_MODELS,
      FEATURES.PROMPT_LIBRARY,
      FEATURES.CONTEXT_BLOCKS,
      FEATURES.CODE_EXECUTION,
      FEATURES.PRIORITY_SUPPORT,
      FEATURES.API_ACCESS,
    ],
    limits: {
      maxConcurrentAgents: 10,
      maxAgentsPerDay: -1, // unlimited
      planningSessionsPerMonth: -1,
      maxContextTokens: 128000,
      promptLibrarySize: -1,
      teamMembers: 10,
    },
  },
  enterprise: {
    features: Object.values(FEATURES),
    limits: {
      maxConcurrentAgents: -1,
      maxAgentsPerDay: -1,
      planningSessionsPerMonth: -1,
      maxContextTokens: -1,
      promptLibrarySize: -1,
      teamMembers: -1,
    },
  },
};
```

### 4.3 Offline License Support

```typescript
interface OfflineLicense {
  // Encrypted payload
  payload: string;              // Base64 encoded, encrypted
  signature: string;            // RSA signature
  
  // Metadata (unencrypted)
  version: number;
  issuedAt: Date;
  validUntil: Date;             // Max 30 days offline
  deviceFingerprint: string;
}

interface OfflineLicensePayload {
  licenseId: string;
  userId: string;
  tier: string;
  features: string[];
  limits: LicenseLimits;
  deviceFingerprint: string;
  issuedAt: number;
  expiresAt: number;
}

// Offline verification flow
class OfflineLicenseVerifier {
  private publicKey: string;
  
  async verify(license: OfflineLicense): Promise<OfflineLicensePayload | null> {
    // 1. Verify signature
    const isValidSignature = await this.verifySignature(
      license.payload,
      license.signature
    );
    if (!isValidSignature) return null;
    
    // 2. Decrypt payload
    const payload = await this.decryptPayload(license.payload);
    
    // 3. Check expiration
    if (Date.now() > payload.expiresAt) return null;
    
    // 4. Verify device fingerprint
    const currentFingerprint = await this.getDeviceFingerprint();
    if (payload.deviceFingerprint !== currentFingerprint) return null;
    
    return payload;
  }
  
  private async getDeviceFingerprint(): Promise<string> {
    // Combine: CPU ID, MAC address, disk serial, hostname
    // Hash with SHA-256
    return hash;
  }
}
```

---

## 5. Model Routing Interface (NeuroForge)

### 5.1 NeuroForge API

```yaml
# NeuroForge Model Routing API
paths:
  /models:
    get:
      summary: List available models
      responses:
        200:
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ModelInfo'

  /models/{modelId}:
    get:
      summary: Get model details
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ModelInfo'

  /chat/completions:
    post:
      summary: Chat completion (OpenAI-compatible)
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ChatCompletionRequest'
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatCompletionResponse'

  /chat/completions/stream:
    post:
      summary: Streaming chat completion
      responses:
        200:
          content:
            text/event-stream:
              schema:
                type: string

  /route:
    post:
      summary: Get optimal model for task
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                taskType: { type: string }
                complexity: { type: string, enum: [low, medium, high] }
                maxCost: { type: number }
                maxLatency: { type: integer }
                requirements: { type: array, items: { type: string } }
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  recommendedModel: { type: string }
                  fallbackModels: { type: array, items: { type: string } }
                  estimatedCost: { type: number }
                  estimatedLatency: { type: integer }

  /ensemble:
    post:
      summary: Multi-model ensemble call
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EnsembleRequest'
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/EnsembleResponse'

components:
  schemas:
    ModelInfo:
      type: object
      properties:
        id: { type: string }
        provider: { type: string }
        name: { type: string }
        displayName: { type: string }
        contextWindow: { type: integer }
        maxOutputTokens: { type: integer }
        inputCostPer1k: { type: number }
        outputCostPer1k: { type: number }
        capabilities: { type: array, items: { type: string } }
        status: { type: string, enum: [available, degraded, unavailable] }

    ChatCompletionRequest:
      type: object
      required: [messages]
      properties:
        model: { type: string }
        messages:
          type: array
          items:
            type: object
            properties:
              role: { type: string }
              content: { type: string }
        temperature: { type: number }
        max_tokens: { type: integer }
        stream: { type: boolean }
        # Routing hints
        routing:
          type: object
          properties:
            preferProvider: { type: string }
            maxCost: { type: number }
            fallbackEnabled: { type: boolean }

    EnsembleRequest:
      type: object
      properties:
        messages: { type: array }
        models: { type: array, items: { type: string } }
        votingStrategy: { type: string, enum: [majority, weighted, best] }
        timeout: { type: integer }

    EnsembleResponse:
      type: object
      properties:
        winner: { type: string }
        responses:
          type: array
          items:
            type: object
            properties:
              model: { type: string }
              content: { type: string }
              score: { type: number }
              latency: { type: integer }
              cost: { type: number }
        consensus: { type: number }
```

### 5.2 Model Router Logic

```typescript
interface ModelRouter {
  // Route to best model
  route(request: RouteRequest): Promise<RoutingDecision>;
  
  // Execute with automatic fallback
  execute(request: ExecutionRequest): Promise<ExecutionResult>;
  
  // Multi-model ensemble
  ensemble(request: EnsembleRequest): Promise<EnsembleResult>;
}

interface RouteRequest {
  taskType: 'chat' | 'code' | 'analysis' | 'creative' | 'planning';
  complexity: 'low' | 'medium' | 'high';
  inputTokens: number;
  maxCost?: number;
  maxLatency?: number;
  requirements?: string[];
  preferProvider?: string;
}

interface RoutingDecision {
  primaryModel: ModelConfig;
  fallbackModels: ModelConfig[];
  estimatedCost: number;
  estimatedLatency: number;
  reasoning: string;
}

// Champion/Shadow model pattern
class ChampionShadowRouter {
  async execute(request: ExecutionRequest): Promise<ExecutionResult> {
    // 1. Route to champion model
    const champion = await this.router.route(request);
    
    // 2. Execute champion
    const championPromise = this.callModel(champion.primaryModel, request);
    
    // 3. Optionally run shadow models (for evaluation, not blocking)
    if (this.config.enableShadowModels) {
      this.runShadowModels(champion.fallbackModels, request);
    }
    
    try {
      // 4. Return champion result
      return await championPromise;
    } catch (error) {
      // 5. Fallback on failure
      for (const fallback of champion.fallbackModels) {
        try {
          return await this.callModel(fallback, request);
        } catch {
          continue;
        }
      }
      throw error;
    }
  }
  
  private async runShadowModels(models: ModelConfig[], request: ExecutionRequest) {
    // Run in background for comparison/evaluation
    // Results stored for model performance analysis
    for (const model of models) {
      this.callModel(model, request)
        .then(result => this.recordShadowResult(model, result))
        .catch(error => this.recordShadowError(model, error));
    }
  }
}
```

---

## 6. Planning Orchestration

### 6.1 Planning Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CORTEX PLANNING ORCHESTRATION                        │
└─────────────────────────────────────────────────────────────────────────┘

  USER                VIBEFORGE              FORGEAGENTS           NEUROFORGE
    │                     │                      │                      │
    │  1. Enter Request   │                      │                      │
    │ ───────────────────►│                      │                      │
    │                     │                      │                      │
    │                     │  2. Estimate Cost    │                      │
    │                     │ ─────────────────────►                      │
    │                     │                      │                      │
    │  3. Show Estimate   │                      │                      │
    │ ◄───────────────────│                      │                      │
    │                     │                      │                      │
    │  4. Confirm Start   │                      │                      │
    │ ───────────────────►│                      │                      │
    │                     │                      │                      │
    │                     │  5. Create Session   │                      │
    │                     │ ─────────────────────►                      │
    │                     │                      │                      │
    │                     │  6. SSE: Started     │                      │
    │ ◄──────────────────────────────────────────│                      │
    │                     │                      │                      │
    │                     │                      │  ┌─────────────────┐ │
    │                     │                      │  │  STAGE 1        │ │
    │                     │                      │  │  ChatGPT        │ │
    │                     │                      │  │  Initial Plan   │ │
    │  7. SSE: Stage 1    │                      │  └────────┬────────┘ │
    │     Progress        │                      │           │          │
    │ ◄──────────────────────────────────────────│◄──────────┘          │
    │     (streaming)     │                      │                      │
    │                     │                      │  ┌─────────────────┐ │
    │                     │                      │  │  STAGE 2        │ │
    │                     │                      │  │  Claude         │ │
    │                     │                      │  │  Review         │ │
    │  8. SSE: Stage 2    │                      │  └────────┬────────┘ │
    │     Progress        │                      │           │          │
    │ ◄──────────────────────────────────────────│◄──────────┘          │
    │                     │                      │                      │
    │                     │                      │  ┌─────────────────┐ │
    │  [Optional Pause]   │                      │  │  User Input     │ │
    │ ◄──────────────────────────────────────────│  │  (if paused)    │ │
    │                     │                      │  └────────┬────────┘ │
    │  9. Inject Context  │                      │           │          │
    │ ───────────────────►│ ─────────────────────►           │          │
    │                     │                      │           │          │
    │                     │                      │  ┌─────────────────┐ │
    │                     │                      │  │  STAGE 3        │ │
    │                     │                      │  │  ChatGPT        │ │
    │                     │                      │  │  Refinement     │ │
    │  10. SSE: Stage 3   │                      │  └────────┬────────┘ │
    │      Progress       │                      │           │          │
    │ ◄──────────────────────────────────────────│◄──────────┘          │
    │                     │                      │                      │
    │                     │                      │  ┌─────────────────┐ │
    │                     │                      │  │  STAGE 4        │ │
    │                     │                      │  │  Claude         │ │
    │                     │                      │  │  Final Plan     │ │
    │  11. SSE: Stage 4   │                      │  └────────┬────────┘ │
    │      Progress       │                      │           │          │
    │ ◄──────────────────────────────────────────│◄──────────┘          │
    │                     │                      │                      │
    │  12. SSE: Complete  │                      │                      │
    │ ◄──────────────────────────────────────────│                      │
    │                     │                      │                      │
    │                     │  13. Get Deliverable │                      │
    │                     │ ─────────────────────►                      │
    │                     │                      │                      │
    │  14. Show Plan +    │                      │                      │
    │      Prompt         │                      │                      │
    │ ◄───────────────────│                      │                      │
    │                     │                      │                      │
    │  15. Copy/Download  │                      │                      │
    │ ───────────────────►│                      │                      │
```

### 6.2 Orchestration State Machine

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PLANNING SESSION STATE MACHINE                        │
└─────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   CREATED    │
                              └──────┬───────┘
                                     │ start()
                                     ▼
                              ┌──────────────┐
                              │   QUEUED     │
                              └──────┬───────┘
                                     │ worker picks up
                                     ▼
                              ┌──────────────┐
              ┌───────────────│ INITIALIZING │───────────────┐
              │               └──────┬───────┘               │
              │                      │ ready                 │ error
              │                      ▼                       ▼
              │               ┌──────────────┐        ┌──────────────┐
              │      ┌───────►│   RUNNING    │───────►│   FAILED     │
              │      │        └──────┬───────┘        └──────────────┘
              │      │               │                       ▲
              │   resume()    pause()│                       │
              │      │               ▼                       │
              │      │        ┌──────────────┐               │
              │      └────────│   PAUSED     │───────────────┤
              │               └──────┬───────┘    cancel()   │
              │                      │                       │
              │               cancel()                       │
              │                      ▼                       │
              │               ┌──────────────┐               │
              └───────────────│  CANCELLED   │◄──────────────┘
                              └──────────────┘
                                     ▲
                                     │
                              ┌──────┴───────┐
                              │  COMPLETED   │
                              └──────────────┘
                                     ▲
                                     │ all stages done
                              ┌──────┴───────┐
                              │   RUNNING    │
                              └──────────────┘

Stage Transitions:
  PENDING → RUNNING → COMPLETED
                   ↘ FAILED
                   ↘ SKIPPED
```

---

## 7. Monitoring & Observability

### 7.1 Logging Strategy

```typescript
interface LogEntry {
  timestamp: Date;
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  service: string;
  traceId: string;
  spanId: string;
  userId?: string;
  agentId?: string;
  taskId?: string;
  message: string;
  context: Record<string, unknown>;
  error?: {
    name: string;
    message: string;
    stack: string;
  };
}

// Structured logging format
const logFormat = {
  timestamp: '2025-12-06T10:30:00.000Z',
  level: 'info',
  service: 'forgeagents',
  traceId: 'abc123',
  spanId: 'def456',
  userId: 'user-789',
  agentId: 'agent-xyz',
  message: 'Agent started execution',
  context: {
    agentType: 'planner',
    pipeline: 'default',
    inputTokens: 1500,
  },
};
```

### 7.2 Metrics

```typescript
// Key metrics to track
const METRICS = {
  // Agent metrics
  'agent.created.total': 'counter',
  'agent.started.total': 'counter',
  'agent.completed.total': 'counter',
  'agent.failed.total': 'counter',
  'agent.duration.seconds': 'histogram',
  'agent.active.count': 'gauge',
  
  // Task metrics
  'task.started.total': 'counter',
  'task.completed.total': 'counter',
  'task.failed.total': 'counter',
  'task.duration.seconds': 'histogram',
  'task.retries.total': 'counter',
  
  // LLM metrics
  'llm.requests.total': 'counter',
  'llm.tokens.input.total': 'counter',
  'llm.tokens.output.total': 'counter',
  'llm.latency.seconds': 'histogram',
  'llm.cost.usd.total': 'counter',
  'llm.errors.total': 'counter',
  
  // API metrics
  'api.requests.total': 'counter',
  'api.latency.seconds': 'histogram',
  'api.errors.total': 'counter',
  
  // License metrics
  'license.checks.total': 'counter',
  'license.denials.total': 'counter',
  'quota.exceeded.total': 'counter',
  
  // System metrics
  'queue.depth': 'gauge',
  'worker.active.count': 'gauge',
  'memory.used.bytes': 'gauge',
  'cpu.usage.percent': 'gauge',
};

// Labels for dimensional metrics
interface MetricLabels {
  service: string;
  environment: string;
  agentType?: string;
  taskType?: string;
  provider?: string;
  model?: string;
  status?: string;
  errorCode?: string;
}
```

### 7.3 Distributed Tracing

```typescript
// OpenTelemetry trace structure
interface Trace {
  traceId: string;
  spans: Span[];
}

interface Span {
  spanId: string;
  parentSpanId?: string;
  operationName: string;
  serviceName: string;
  startTime: Date;
  endTime: Date;
  status: 'ok' | 'error';
  attributes: Record<string, string | number | boolean>;
  events: SpanEvent[];
}

// Example trace for planning session
const planningTrace = {
  traceId: 'planning-session-123',
  spans: [
    {
      spanId: 'api-request',
      operationName: 'POST /cortex/sessions',
      serviceName: 'forgeagents',
      attributes: { 'http.method': 'POST', 'http.url': '/cortex/sessions' },
    },
    {
      spanId: 'license-check',
      parentSpanId: 'api-request',
      operationName: 'verify_license',
      serviceName: 'forgeagents',
      attributes: { 'license.tier': 'pro', 'feature': 'cortex.multi_ai' },
    },
    {
      spanId: 'stage-1',
      parentSpanId: 'api-request',
      operationName: 'execute_stage',
      serviceName: 'forgeagents',
      attributes: { 'stage.type': 'initial', 'stage.index': 0 },
    },
    {
      spanId: 'llm-call-1',
      parentSpanId: 'stage-1',
      operationName: 'chat_completion',
      serviceName: 'neuroforge',
      attributes: { 'model': 'gpt-4o', 'provider': 'openai', 'tokens.input': 1500 },
    },
    // ... more spans
  ],
};
```

### 7.4 Health Checks

```typescript
// Health check endpoints
interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  checks: {
    [name: string]: {
      status: 'pass' | 'warn' | 'fail';
      message?: string;
      latency?: number;
    };
  };
}

// GET /health
const healthResponse: HealthStatus = {
  status: 'healthy',
  version: '1.0.0',
  uptime: 86400,
  checks: {
    database: { status: 'pass', latency: 5 },
    redis: { status: 'pass', latency: 2 },
    rabbitmq: { status: 'pass', latency: 3 },
    neuroforge: { status: 'pass', latency: 50 },
    dataforge: { status: 'pass', latency: 10 },
  },
};

// GET /health/live (Kubernetes liveness)
// Returns 200 if process is running

// GET /health/ready (Kubernetes readiness)
// Returns 200 if ready to accept traffic
```

---

## 8. Security Posture

### 8.1 Authentication & Authorization

```typescript
// JWT token structure
interface JWTPayload {
  // Standard claims
  sub: string;              // User ID
  iat: number;              // Issued at
  exp: number;              // Expiration
  jti: string;              // Token ID (for revocation)
  
  // Custom claims
  email: string;
  organizationId?: string;
  tier: string;
  deviceId: string;
  applicationId: string;
  permissions: string[];
}

// Permission model
const PERMISSIONS = {
  // Agents
  'agents:create': 'Create agents',
  'agents:read': 'View agents',
  'agents:update': 'Modify agents',
  'agents:delete': 'Delete agents',
  'agents:execute': 'Run agents',
  
  // Cortex
  'cortex:create': 'Create planning sessions',
  'cortex:read': 'View planning sessions',
  
  // Admin
  'admin:users': 'Manage users',
  'admin:licenses': 'Manage licenses',
  'admin:settings': 'Manage settings',
} as const;

// Role definitions
const ROLES = {
  user: ['agents:create', 'agents:read', 'agents:execute', 'cortex:create', 'cortex:read'],
  pro: ['agents:*', 'cortex:*'],
  admin: ['*'],
};
```

### 8.2 API Security

```typescript
// Rate limiting configuration
interface RateLimitConfig {
  // Per-user limits
  requestsPerMinute: number;
  requestsPerHour: number;
  requestsPerDay: number;
  
  // Per-endpoint limits
  endpoints: {
    [path: string]: {
      requestsPerMinute: number;
      burstLimit: number;
    };
  };
  
  // Special limits
  streamingConnections: number;
  concurrentAgents: number;
}

const rateLimits: RateLimitConfig = {
  requestsPerMinute: 60,
  requestsPerHour: 1000,
  requestsPerDay: 10000,
  endpoints: {
    '/cortex/sessions': { requestsPerMinute: 10, burstLimit: 5 },
    '/agents': { requestsPerMinute: 20, burstLimit: 10 },
    '/chat/completions': { requestsPerMinute: 30, burstLimit: 15 },
  },
  streamingConnections: 5,
  concurrentAgents: 10,
};

// API key rotation
interface APIKey {
  id: string;
  userId: string;
  name: string;
  keyHash: string;            // SHA-256 hash
  prefix: string;             // First 8 chars for identification
  permissions: string[];
  rateLimit?: Partial<RateLimitConfig>;
  expiresAt?: Date;
  lastUsedAt?: Date;
  createdAt: Date;
  isActive: boolean;
}
```

### 8.3 Agent Sandboxing

```typescript
// Agent execution sandbox
interface SandboxConfig {
  // Resource limits
  maxMemoryMB: number;
  maxCPUPercent: number;
  maxExecutionSeconds: number;
  maxFileDescriptors: number;
  
  // Network restrictions
  allowNetwork: boolean;
  allowedDomains: string[];
  blockedPorts: number[];
  
  // Filesystem restrictions
  allowFilesystem: boolean;
  readOnlyPaths: string[];
  writablePaths: string[];
  maxFileSizeMB: number;
  
  // Code execution
  allowCodeExecution: boolean;
  allowedLanguages: string[];
  maxOutputSizeKB: number;
}

const defaultSandbox: SandboxConfig = {
  maxMemoryMB: 512,
  maxCPUPercent: 50,
  maxExecutionSeconds: 300,
  maxFileDescriptors: 100,
  
  allowNetwork: false,
  allowedDomains: [],
  blockedPorts: [22, 23, 25, 445, 3389],
  
  allowFilesystem: false,
  readOnlyPaths: [],
  writablePaths: [],
  maxFileSizeMB: 10,
  
  allowCodeExecution: false,
  allowedLanguages: [],
  maxOutputSizeKB: 100,
};
```

### 8.4 Data Protection

```typescript
// Data handling policies
interface DataPolicy {
  // Retention
  sessionRetentionDays: number;
  logRetentionDays: number;
  auditRetentionDays: number;
  
  // Encryption
  encryptAtRest: boolean;
  encryptInTransit: boolean;
  keyRotationDays: number;
  
  // PII handling
  allowPII: boolean;
  piiDetection: boolean;
  piiRedaction: boolean;
  
  // Export
  allowDataExport: boolean;
  exportFormats: string[];
}

// Audit logging
interface AuditEvent {
  id: string;
  timestamp: Date;
  userId: string;
  action: string;
  resource: string;
  resourceId: string;
  ipAddress: string;
  userAgent: string;
  status: 'success' | 'failure';
  details: Record<string, unknown>;
}
```

---

## 9. Failure Modes & Recovery

### 9.1 Failure Categories

```typescript
// Failure taxonomy
const FAILURE_MODES = {
  // Transient (auto-retry)
  TRANSIENT: {
    LLM_TIMEOUT: { retryable: true, maxRetries: 3, backoff: 'exponential' },
    LLM_RATE_LIMIT: { retryable: true, maxRetries: 5, backoff: 'fixed', delay: 60000 },
    NETWORK_ERROR: { retryable: true, maxRetries: 3, backoff: 'exponential' },
    SERVICE_UNAVAILABLE: { retryable: true, maxRetries: 3, backoff: 'exponential' },
  },
  
  // Recoverable (checkpoint resume)
  RECOVERABLE: {
    WORKER_CRASH: { action: 'resume_from_checkpoint' },
    SESSION_TIMEOUT: { action: 'resume_from_checkpoint' },
    USER_INTERRUPT: { action: 'pause_and_wait' },
  },
  
  // Fatal (fail fast)
  FATAL: {
    INVALID_INPUT: { action: 'fail_immediately' },
    AUTH_FAILURE: { action: 'fail_immediately' },
    QUOTA_EXCEEDED: { action: 'fail_immediately' },
    INVALID_API_KEY: { action: 'fail_immediately' },
  },
};
```

### 9.2 Recovery Strategies

```typescript
// Checkpoint-based recovery
interface Checkpoint {
  id: string;
  sessionId: string;
  stageIndex: number;
  state: {
    completedStages: number[];
    stageOutputs: Record<number, string>;
    context: string;
    metrics: {
      tokensUsed: number;
      cost: number;
      duration: number;
    };
  };
  createdAt: Date;
  expiresAt: Date;
}

class RecoveryManager {
  async recoverSession(sessionId: string): Promise<PlanningSession> {
    // 1. Load latest checkpoint
    const checkpoint = await this.loadCheckpoint(sessionId);
    if (!checkpoint) {
      throw new Error('No checkpoint available');
    }
    
    // 2. Verify checkpoint validity
    if (checkpoint.expiresAt < new Date()) {
      throw new Error('Checkpoint expired');
    }
    
    // 3. Restore session state
    const session = await this.restoreSession(checkpoint);
    
    // 4. Resume from next stage
    return this.resumeExecution(session, checkpoint.stageIndex + 1);
  }
}

// Circuit breaker for external services
class CircuitBreaker {
  private state: 'closed' | 'open' | 'half-open' = 'closed';
  private failures = 0;
  private lastFailure?: Date;
  
  constructor(
    private readonly threshold: number = 5,
    private readonly timeout: number = 60000,
  ) {}
  
  async execute<T>(operation: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (Date.now() - (this.lastFailure?.getTime() || 0) > this.timeout) {
        this.state = 'half-open';
      } else {
        throw new Error('Circuit breaker is open');
      }
    }
    
    try {
      const result = await operation();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }
  
  private onSuccess() {
    this.failures = 0;
    this.state = 'closed';
  }
  
  private onFailure() {
    this.failures++;
    this.lastFailure = new Date();
    if (this.failures >= this.threshold) {
      this.state = 'open';
    }
  }
}
```

### 9.3 Graceful Degradation

```typescript
// Degradation levels
type DegradationLevel = 'full' | 'limited' | 'minimal' | 'offline';

interface DegradationConfig {
  level: DegradationLevel;
  features: {
    [feature: string]: boolean;
  };
  fallbacks: {
    [service: string]: string;
  };
}

const degradationLevels: Record<DegradationLevel, DegradationConfig> = {
  full: {
    level: 'full',
    features: {
      planning: true,
      agents: true,
      streaming: true,
      ensemble: true,
    },
    fallbacks: {},
  },
  limited: {
    level: 'limited',
    features: {
      planning: true,
      agents: true,
      streaming: false,  // Fall back to polling
      ensemble: false,   // Single model only
    },
    fallbacks: {
      streaming: 'polling',
    },
  },
  minimal: {
    level: 'minimal',
    features: {
      planning: false,
      agents: true,      // Basic agents only
      streaming: false,
      ensemble: false,
    },
    fallbacks: {
      planning: 'queue_for_later',
    },
  },
  offline: {
    level: 'offline',
    features: {
      planning: false,
      agents: false,
      streaming: false,
      ensemble: false,
    },
    fallbacks: {
      all: 'local_cache',
    },
  },
};
```

---

## Appendix A: Quick Reference

### Service Ports

| Service | Port | Protocol |
|---------|------|----------|
| VibeForge (Desktop) | - | Tauri |
| ForgeAgents | 8002 | HTTP/WSS |
| NeuroForge | 8000 | HTTP |
| DataForge | 8001 | HTTP |
| Rake | 8003 | HTTP |
| PostgreSQL | 5432 | TCP |
| Redis | 6379 | TCP |
| RabbitMQ | 5672/15672 | AMQP/HTTP |

### Environment Variables

```bash
# ForgeAgents
FORGEAGENTS_PORT=8002
FORGEAGENTS_LOG_LEVEL=info
FORGEAGENTS_JWT_SECRET=xxx
FORGEAGENTS_DATABASE_URL=postgresql://...
FORGEAGENTS_REDIS_URL=redis://...
FORGEAGENTS_RABBITMQ_URL=amqp://...
FORGEAGENTS_NEUROFORGE_URL=http://localhost:8000
FORGEAGENTS_DATAFORGE_URL=http://localhost:8001

# NeuroForge
NEUROFORGE_PORT=8000
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
XAI_API_KEY=xai-xxx
GOOGLE_AI_API_KEY=xxx

# DataForge
DATAFORGE_PORT=8001
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

---

**Document Version:** 2.0  
**Last Updated:** December 6, 2025  
**Status:** Implementation-Ready
