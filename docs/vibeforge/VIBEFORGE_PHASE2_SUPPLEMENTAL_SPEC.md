# VibeForge Phase 2: Supplemental Specification

**Version:** 1.0  
**Date:** December 6, 2025  
**Purpose:** Address gaps identified in architecture review

This document supplements the main Architecture Specification with:
1. Rate limiting & concurrency policies
2. SSE reconnection logic
3. Worker process management
4. License enforcement hooks
5. NeuroForge routing logic
6. DataForge storage schemas
7. Multi-tenant isolation

---

## Table of Contents

1. [Rate Limiting & Concurrency](#1-rate-limiting--concurrency)
2. [SSE Reconnection Protocol](#2-sse-reconnection-protocol)
3. [Worker Process Management](#3-worker-process-management)
4. [License Enforcement Hooks](#4-license-enforcement-hooks)
5. [NeuroForge Routing Logic](#5-neuroforge-routing-logic)
6. [DataForge Storage Schemas](#6-dataforge-storage-schemas)
7. [Multi-Tenant Isolation](#7-multi-tenant-isolation)
8. [API Route Reconciliation](#8-api-route-reconciliation)

---

## 1. Rate Limiting & Concurrency

### 1.1 Session Concurrency Limits by Tier

```typescript
interface ConcurrencyLimits {
  // Active planning sessions
  maxConcurrentPlanningSessions: number;
  
  // Active agents
  maxConcurrentAgents: number;
  
  // SSE connections
  maxSSEConnections: number;
  
  // Queue depth (pending sessions)
  maxQueuedSessions: number;
}

const TIER_CONCURRENCY: Record<string, ConcurrencyLimits> = {
  free: {
    maxConcurrentPlanningSessions: 1,
    maxConcurrentAgents: 1,
    maxSSEConnections: 2,
    maxQueuedSessions: 2,
  },
  trial: {
    maxConcurrentPlanningSessions: 3,
    maxConcurrentAgents: 5,
    maxSSEConnections: 5,
    maxQueuedSessions: 10,
  },
  pro: {
    maxConcurrentPlanningSessions: 10,
    maxConcurrentAgents: 20,
    maxSSEConnections: 15,
    maxQueuedSessions: 50,
  },
  enterprise: {
    maxConcurrentPlanningSessions: -1,  // unlimited
    maxConcurrentAgents: -1,
    maxSSEConnections: 100,
    maxQueuedSessions: -1,
  },
};
```

### 1.2 Rate Limit Configuration

```typescript
interface RateLimitRule {
  endpoint: string;
  method: string;
  limits: {
    perSecond?: number;
    perMinute?: number;
    perHour?: number;
    perDay?: number;
  };
  burstSize: number;
  tierMultipliers: Record<string, number>;
}

const RATE_LIMIT_RULES: RateLimitRule[] = [
  // Cortex Planning
  {
    endpoint: '/api/v1/cortex/sessions',
    method: 'POST',
    limits: { perMinute: 5, perHour: 20, perDay: 100 },
    burstSize: 3,
    tierMultipliers: { free: 0.2, trial: 1, pro: 5, enterprise: 20 },
  },
  {
    endpoint: '/api/v1/cortex/sessions/stream',
    method: 'POST',
    limits: { perMinute: 5, perHour: 20 },
    burstSize: 2,
    tierMultipliers: { free: 0.2, trial: 1, pro: 5, enterprise: 20 },
  },
  {
    endpoint: '/api/v1/cortex/estimate',
    method: 'POST',
    limits: { perMinute: 30, perHour: 200 },
    burstSize: 10,
    tierMultipliers: { free: 1, trial: 1, pro: 2, enterprise: 5 },
  },
  
  // Agents
  {
    endpoint: '/api/v1/agents',
    method: 'POST',
    limits: { perMinute: 10, perHour: 50, perDay: 200 },
    burstSize: 5,
    tierMultipliers: { free: 0.25, trial: 1, pro: 5, enterprise: 20 },
  },
  {
    endpoint: '/api/v1/agents/{id}/events',
    method: 'GET',
    limits: { perMinute: 60 },  // SSE connection attempts
    burstSize: 10,
    tierMultipliers: { free: 1, trial: 1, pro: 1, enterprise: 1 },
  },
  
  // LLM Calls (via NeuroForge)
  {
    endpoint: '/api/v1/chat/completions',
    method: 'POST',
    limits: { perMinute: 20, perHour: 200 },
    burstSize: 5,
    tierMultipliers: { free: 0.5, trial: 1, pro: 3, enterprise: 10 },
  },
  
  // License
  {
    endpoint: '/api/v1/license/verify',
    method: 'POST',
    limits: { perMinute: 100 },  // High limit, cached
    burstSize: 20,
    tierMultipliers: { free: 1, trial: 1, pro: 1, enterprise: 1 },
  },
];
```

### 1.3 Rate Limiter Implementation

```typescript
// Redis-based sliding window rate limiter
class RateLimiter {
  constructor(private redis: Redis) {}

  async checkLimit(
    key: string,
    rule: RateLimitRule,
    tier: string,
  ): Promise<RateLimitResult> {
    const multiplier = rule.tierMultipliers[tier] || 1;
    const now = Date.now();
    
    const results: boolean[] = [];
    
    // Check each time window
    if (rule.limits.perSecond) {
      results.push(await this.checkWindow(
        `${key}:sec:${Math.floor(now / 1000)}`,
        rule.limits.perSecond * multiplier,
        1,
      ));
    }
    
    if (rule.limits.perMinute) {
      results.push(await this.checkWindow(
        `${key}:min:${Math.floor(now / 60000)}`,
        rule.limits.perMinute * multiplier,
        60,
      ));
    }
    
    if (rule.limits.perHour) {
      results.push(await this.checkWindow(
        `${key}:hour:${Math.floor(now / 3600000)}`,
        rule.limits.perHour * multiplier,
        3600,
      ));
    }
    
    if (rule.limits.perDay) {
      results.push(await this.checkWindow(
        `${key}:day:${Math.floor(now / 86400000)}`,
        rule.limits.perDay * multiplier,
        86400,
      ));
    }
    
    const allowed = results.every(r => r);
    
    return {
      allowed,
      remaining: await this.getRemaining(key, rule, tier),
      resetAt: this.getResetTime(rule),
    };
  }

  private async checkWindow(
    key: string,
    limit: number,
    ttlSeconds: number,
  ): Promise<boolean> {
    const count = await this.redis.incr(key);
    if (count === 1) {
      await this.redis.expire(key, ttlSeconds);
    }
    return count <= limit;
  }
}

interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetAt: Date;
  retryAfter?: number;  // seconds
}
```

### 1.4 Concurrency Enforcement

```typescript
class ConcurrencyManager {
  constructor(private redis: Redis) {}

  async acquireSlot(
    userId: string,
    resourceType: 'planning' | 'agent' | 'sse',
    tier: string,
  ): Promise<ConcurrencyResult> {
    const limits = TIER_CONCURRENCY[tier];
    const limitKey = this.getLimitKey(resourceType, limits);
    const countKey = `concurrency:${userId}:${resourceType}`;
    
    // Atomic check-and-increment
    const script = `
      local current = tonumber(redis.call('GET', KEYS[1]) or '0')
      local limit = tonumber(ARGV[1])
      if limit == -1 or current < limit then
        redis.call('INCR', KEYS[1])
        redis.call('EXPIRE', KEYS[1], 86400)
        return 1
      end
      return 0
    `;
    
    const acquired = await this.redis.eval(script, 1, countKey, limitKey);
    
    if (!acquired) {
      const current = await this.redis.get(countKey);
      return {
        acquired: false,
        current: parseInt(current || '0'),
        limit: limitKey,
        queuePosition: await this.getQueuePosition(userId, resourceType),
      };
    }
    
    return { acquired: true, current: 1, limit: limitKey };
  }

  async releaseSlot(
    userId: string,
    resourceType: 'planning' | 'agent' | 'sse',
  ): Promise<void> {
    const countKey = `concurrency:${userId}:${resourceType}`;
    await this.redis.decr(countKey);
  }

  private getLimitKey(
    resourceType: string,
    limits: ConcurrencyLimits,
  ): number {
    switch (resourceType) {
      case 'planning': return limits.maxConcurrentPlanningSessions;
      case 'agent': return limits.maxConcurrentAgents;
      case 'sse': return limits.maxSSEConnections;
      default: return 1;
    }
  }
}

interface ConcurrencyResult {
  acquired: boolean;
  current: number;
  limit: number;
  queuePosition?: number;
}
```

---

## 2. SSE Reconnection Protocol

### 2.1 Client-Side SSE Manager

```typescript
/**
 * Robust SSE client with reconnection, resume, and backoff
 */
class SSEManager {
  private eventSource: EventSource | null = null;
  private lastEventId: string | null = null;
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private abortController: AbortController | null = null;
  
  private readonly config: SSEConfig = {
    maxReconnectAttempts: 10,
    baseReconnectDelay: 1000,      // 1 second
    maxReconnectDelay: 30000,      // 30 seconds
    reconnectBackoffMultiplier: 2,
    heartbeatTimeout: 30000,       // 30 seconds
    jitterFactor: 0.3,
  };

  constructor(
    private readonly baseUrl: string,
    private readonly handlers: SSEHandlers,
  ) {}

  /**
   * Start streaming session with POST (for request body)
   */
  async startStream(
    endpoint: string,
    body: Record<string, unknown>,
  ): Promise<void> {
    this.abortController = new AbortController();
    this.reconnectAttempts = 0;
    
    await this.connect(endpoint, body);
  }

  private async connect(
    endpoint: string,
    body: Record<string, unknown>,
  ): Promise<void> {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      };
      
      // Include last event ID for resume
      if (this.lastEventId) {
        headers['Last-Event-ID'] = this.lastEventId;
      }
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: this.abortController?.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      // Reset reconnect attempts on successful connection
      this.reconnectAttempts = 0;
      this.handlers.onConnect?.();

      await this.processStream(reader, endpoint, body);
      
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        return; // Intentional disconnect
      }
      
      this.handlers.onError?.(error as Error);
      await this.scheduleReconnect(endpoint, body);
    }
  }

  private async processStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    endpoint: string,
    body: Record<string, unknown>,
  ): Promise<void> {
    const decoder = new TextDecoder();
    let buffer = '';
    let heartbeatTimer = this.startHeartbeatMonitor(endpoint, body);

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Stream ended normally
          this.handlers.onComplete?.();
          break;
        }

        // Reset heartbeat timer on any data
        clearTimeout(heartbeatTimer);
        heartbeatTimer = this.startHeartbeatMonitor(endpoint, body);

        buffer += decoder.decode(value, { stream: true });
        
        // Process complete events
        const events = this.parseEvents(buffer);
        buffer = events.remaining;
        
        for (const event of events.parsed) {
          this.handleEvent(event);
        }
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        this.handlers.onError?.(error as Error);
        await this.scheduleReconnect(endpoint, body);
      }
    } finally {
      clearTimeout(heartbeatTimer);
    }
  }

  private parseEvents(buffer: string): { parsed: SSEEvent[]; remaining: string } {
    const events: SSEEvent[] = [];
    const lines = buffer.split('\n');
    
    let currentEvent: Partial<SSEEvent> = {};
    let dataLines: string[] = [];
    let remaining = '';
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Check if this might be an incomplete event
      if (i === lines.length - 1 && line !== '') {
        remaining = lines.slice(i).join('\n');
        break;
      }
      
      if (line === '') {
        // Empty line = end of event
        if (dataLines.length > 0 || currentEvent.event) {
          events.push({
            event: currentEvent.event || 'message',
            data: dataLines.join('\n'),
            id: currentEvent.id,
            retry: currentEvent.retry,
          });
        }
        currentEvent = {};
        dataLines = [];
        continue;
      }
      
      const colonIndex = line.indexOf(':');
      if (colonIndex === 0) {
        // Comment, ignore
        continue;
      }
      
      const field = colonIndex > 0 ? line.slice(0, colonIndex) : line;
      const value = colonIndex > 0 ? line.slice(colonIndex + 1).trimStart() : '';
      
      switch (field) {
        case 'event':
          currentEvent.event = value;
          break;
        case 'data':
          dataLines.push(value);
          break;
        case 'id':
          currentEvent.id = value;
          break;
        case 'retry':
          currentEvent.retry = parseInt(value, 10);
          break;
      }
    }
    
    return { parsed: events, remaining };
  }

  private handleEvent(event: SSEEvent): void {
    // Update last event ID for resume
    if (event.id) {
      this.lastEventId = event.id;
    }
    
    // Update reconnect delay if server suggests
    if (event.retry) {
      this.config.baseReconnectDelay = event.retry;
    }
    
    // Handle heartbeat internally
    if (event.event === 'heartbeat') {
      return;
    }
    
    // Parse data and dispatch
    try {
      const data = JSON.parse(event.data);
      this.handlers.onEvent?.(event.event, data);
    } catch {
      // Non-JSON data
      this.handlers.onEvent?.(event.event, { raw: event.data });
    }
  }

  private startHeartbeatMonitor(
    endpoint: string,
    body: Record<string, unknown>,
  ): ReturnType<typeof setTimeout> {
    return setTimeout(() => {
      this.handlers.onError?.(new Error('Heartbeat timeout'));
      this.scheduleReconnect(endpoint, body);
    }, this.config.heartbeatTimeout);
  }

  private async scheduleReconnect(
    endpoint: string,
    body: Record<string, unknown>,
  ): Promise<void> {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.handlers.onMaxRetriesExceeded?.();
      return;
    }
    
    this.reconnectAttempts++;
    
    // Calculate delay with exponential backoff and jitter
    const baseDelay = Math.min(
      this.config.baseReconnectDelay * 
        Math.pow(this.config.reconnectBackoffMultiplier, this.reconnectAttempts - 1),
      this.config.maxReconnectDelay,
    );
    
    const jitter = baseDelay * this.config.jitterFactor * (Math.random() - 0.5);
    const delay = Math.round(baseDelay + jitter);
    
    this.handlers.onReconnecting?.(this.reconnectAttempts, delay);
    
    await new Promise(resolve => {
      this.reconnectTimer = setTimeout(resolve, delay);
    });
    
    if (!this.abortController?.signal.aborted) {
      await this.connect(endpoint, body);
    }
  }

  /**
   * Gracefully disconnect
   */
  disconnect(): void {
    this.abortController?.abort();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.lastEventId = null;
    this.reconnectAttempts = 0;
    this.handlers.onDisconnect?.();
  }
}

interface SSEConfig {
  maxReconnectAttempts: number;
  baseReconnectDelay: number;
  maxReconnectDelay: number;
  reconnectBackoffMultiplier: number;
  heartbeatTimeout: number;
  jitterFactor: number;
}

interface SSEEvent {
  event: string;
  data: string;
  id?: string;
  retry?: number;
}

interface SSEHandlers {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onEvent?: (event: string, data: Record<string, unknown>) => void;
  onError?: (error: Error) => void;
  onReconnecting?: (attempt: number, delay: number) => void;
  onMaxRetriesExceeded?: () => void;
  onComplete?: () => void;
}
```

### 2.2 Server-Side SSE Support

```python
# ForgeAgents SSE endpoint with resume support

from fastapi import Request
from fastapi.responses import StreamingResponse
import asyncio
from datetime import datetime
from typing import AsyncGenerator

class SSESession:
    """Manages SSE session with event history for resume"""
    
    def __init__(self, session_id: str, max_history: int = 100):
        self.session_id = session_id
        self.max_history = max_history
        self.events: list[dict] = []
        self.event_counter = 0
        self.last_heartbeat = datetime.utcnow()
    
    def add_event(self, event_type: str, data: dict) -> str:
        """Add event and return event ID"""
        self.event_counter += 1
        event_id = f"{self.session_id}-{self.event_counter}"
        
        event = {
            "id": event_id,
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.events.append(event)
        
        # Trim history
        if len(self.events) > self.max_history:
            self.events = self.events[-self.max_history:]
        
        return event_id
    
    def get_events_since(self, last_event_id: str | None) -> list[dict]:
        """Get all events after the given event ID"""
        if not last_event_id:
            return []
        
        for i, event in enumerate(self.events):
            if event["id"] == last_event_id:
                return self.events[i + 1:]
        
        return []


def format_sse(event: dict) -> str:
    """Format event as SSE string"""
    lines = []
    
    if event.get("id"):
        lines.append(f"id: {event['id']}")
    
    lines.append(f"event: {event['event']}")
    
    import json
    data = json.dumps(event["data"])
    lines.append(f"data: {data}")
    
    lines.append("")  # Empty line terminates event
    
    return "\n".join(lines) + "\n"


async def stream_planning_session(
    request: Request,
    session: SSESession,
    agent: CortexAgent,
    planning_request: PlanningRequest,
) -> AsyncGenerator[str, None]:
    """Stream planning session events with resume support"""
    
    # Check for resume
    last_event_id = request.headers.get("Last-Event-ID")
    
    if last_event_id:
        # Send missed events
        missed_events = session.get_events_since(last_event_id)
        for event in missed_events:
            yield format_sse(event)
    
    # Event queue for this stream
    event_queue: asyncio.Queue = asyncio.Queue()
    
    # Heartbeat task
    async def send_heartbeat():
        while True:
            await asyncio.sleep(15)  # Every 15 seconds
            event_id = session.add_event("heartbeat", {"timestamp": datetime.utcnow().isoformat()})
            await event_queue.put({"id": event_id, "event": "heartbeat", "data": {}})
    
    heartbeat_task = asyncio.create_task(send_heartbeat())
    
    # Callbacks to push events
    def on_stage_start(index: int, stage_type: str):
        event_id = session.add_event("stage_started", {"stage_index": index, "stage_type": stage_type})
        event_queue.put_nowait({"id": event_id, "event": "stage_started", "data": {"stage_index": index, "stage_type": stage_type}})
    
    def on_stage_progress(index: int, token: str):
        # Don't store progress events in history (too many)
        event_queue.put_nowait({"event": "stage_progress", "data": {"stage_index": index, "token": token}})
    
    def on_stage_complete(index: int, result: dict):
        event_id = session.add_event("stage_completed", {"stage_index": index, **result})
        event_queue.put_nowait({"id": event_id, "event": "stage_completed", "data": {"stage_index": index, **result}})
    
    def on_session_complete(result: dict):
        event_id = session.add_event("session_completed", result)
        event_queue.put_nowait({"id": event_id, "event": "session_completed", "data": result})
        event_queue.put_nowait(None)  # Signal end
    
    def on_session_failed(error: str):
        event_id = session.add_event("session_failed", {"error": error})
        event_queue.put_nowait({"id": event_id, "event": "session_failed", "data": {"error": error}})
        event_queue.put_nowait(None)
    
    # Start agent execution
    execution_task = asyncio.create_task(
        agent.start_session(
            planning_request,
            on_stage_start=on_stage_start,
            on_stage_progress=on_stage_progress,
            on_stage_complete=on_stage_complete,
            on_session_complete=on_session_complete,
        )
    )
    
    # Yield initial event
    event_id = session.add_event("session_started", {"session_id": session.session_id})
    yield format_sse({"id": event_id, "event": "session_started", "data": {"session_id": session.session_id}})
    
    try:
        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                break
            
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                
                if event is None:
                    break  # Session complete
                
                yield format_sse(event)
                
            except asyncio.TimeoutError:
                continue
    
    finally:
        heartbeat_task.cancel()
        execution_task.cancel()
```

---

## 3. Worker Process Management

### 3.1 Worker Manager Specification

```typescript
interface WorkerManagerConfig {
  // Scaling
  minWorkers: number;
  maxWorkers: number;
  targetQueueDepth: number;  // Scale up when queue exceeds this
  
  // Timing
  workerIdleTimeout: number;  // Kill idle workers after this (ms)
  workerMaxLifetime: number;  // Restart workers after this (ms)
  healthCheckInterval: number;
  
  // Task assignment
  taskTimeout: number;
  maxTaskRetries: number;
  
  // Queue
  queueType: 'rabbitmq' | 'redis' | 'memory';
  prefetchCount: number;  // Tasks per worker
}

const DEFAULT_WORKER_CONFIG: WorkerManagerConfig = {
  minWorkers: 2,
  maxWorkers: 10,
  targetQueueDepth: 5,
  
  workerIdleTimeout: 300000,      // 5 minutes
  workerMaxLifetime: 3600000,     // 1 hour
  healthCheckInterval: 30000,     // 30 seconds
  
  taskTimeout: 600000,            // 10 minutes
  maxTaskRetries: 3,
  
  queueType: 'rabbitmq',
  prefetchCount: 1,
};
```

### 3.2 Worker Manager Implementation

```python
# forgeagents/workers/manager.py

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class WorkerInfo:
    id: str
    process_id: int
    status: str  # idle, busy, stopping, dead
    started_at: datetime
    last_activity: datetime
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_task_id: Optional[str] = None


@dataclass
class TaskInfo:
    id: str
    type: str
    payload: dict
    created_at: datetime
    started_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    attempts: int = 0
    status: str = "pending"  # pending, running, completed, failed


class WorkerManager:
    """
    Manages a pool of worker processes for task execution.
    
    Responsibilities:
    - Spawn/kill workers based on queue depth
    - Route tasks to available workers
    - Handle worker failures and restarts
    - Track task completion and retries
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.workers: Dict[str, WorkerInfo] = {}
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start the worker manager"""
        self._running = True
        
        # Start minimum workers
        for _ in range(self.config["min_workers"]):
            await self._spawn_worker()
        
        # Start management tasks
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._scaling_loop())
        asyncio.create_task(self._dispatch_loop())
        
        logger.info(f"Worker manager started with {len(self.workers)} workers")
    
    async def stop(self):
        """Gracefully stop all workers"""
        self._running = False
        
        # Signal all workers to stop
        for worker_id in list(self.workers.keys()):
            await self._stop_worker(worker_id)
        
        logger.info("Worker manager stopped")
    
    async def submit_task(self, task_type: str, payload: dict) -> str:
        """Submit a task to the queue"""
        task_id = str(uuid4())
        task = TaskInfo(
            id=task_id,
            type=task_type,
            payload=payload,
            created_at=datetime.utcnow(),
        )
        
        self.tasks[task_id] = task
        await self.task_queue.put(task_id)
        
        logger.info(f"Task {task_id} submitted, queue depth: {self.task_queue.qsize()}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status"""
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        if task.status == "pending":
            task.status = "cancelled"
            return True
        
        if task.status == "running" and task.worker_id:
            # Signal worker to cancel
            await self._signal_worker(task.worker_id, "cancel_task", task_id)
            return True
        
        return False
    
    # Private methods
    
    async def _spawn_worker(self) -> str:
        """Spawn a new worker process"""
        worker_id = str(uuid4())
        
        # In production, this would spawn a subprocess or container
        # For now, simulating with asyncio task
        process_id = id(asyncio.current_task())
        
        worker = WorkerInfo(
            id=worker_id,
            process_id=process_id,
            status="idle",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        
        self.workers[worker_id] = worker
        
        # Start worker task
        asyncio.create_task(self._worker_loop(worker_id))
        
        logger.info(f"Spawned worker {worker_id}")
        return worker_id
    
    async def _stop_worker(self, worker_id: str):
        """Stop a worker gracefully"""
        worker = self.workers.get(worker_id)
        if not worker:
            return
        
        worker.status = "stopping"
        
        # Wait for current task to complete (with timeout)
        timeout = 30  # seconds
        start = datetime.utcnow()
        
        while worker.current_task_id and (datetime.utcnow() - start).seconds < timeout:
            await asyncio.sleep(1)
        
        # Force stop if still running
        worker.status = "dead"
        del self.workers[worker_id]
        
        logger.info(f"Stopped worker {worker_id}")
    
    async def _worker_loop(self, worker_id: str):
        """Main worker loop"""
        worker = self.workers[worker_id]
        
        while self._running and worker.status != "stopping":
            try:
                # Get next task
                task_id = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0,
                )
                
                task = self.tasks.get(task_id)
                if not task or task.status == "cancelled":
                    continue
                
                # Execute task
                worker.status = "busy"
                worker.current_task_id = task_id
                worker.last_activity = datetime.utcnow()
                
                task.status = "running"
                task.started_at = datetime.utcnow()
                task.worker_id = worker_id
                task.attempts += 1
                
                try:
                    await self._execute_task(task)
                    task.status = "completed"
                    worker.tasks_completed += 1
                    
                except asyncio.TimeoutError:
                    task.status = "timeout"
                    await self._handle_task_failure(task, "timeout")
                    
                except Exception as e:
                    task.status = "failed"
                    await self._handle_task_failure(task, str(e))
                    worker.tasks_failed += 1
                
                finally:
                    worker.status = "idle"
                    worker.current_task_id = None
                    worker.last_activity = datetime.utcnow()
            
            except asyncio.TimeoutError:
                # No task available, check idle timeout
                idle_time = (datetime.utcnow() - worker.last_activity).total_seconds() * 1000
                
                if (
                    idle_time > self.config["worker_idle_timeout"]
                    and len(self.workers) > self.config["min_workers"]
                ):
                    logger.info(f"Worker {worker_id} idle timeout, stopping")
                    break
            
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        # Cleanup
        if worker_id in self.workers:
            del self.workers[worker_id]
    
    async def _execute_task(self, task: TaskInfo):
        """Execute a task (override in subclass)"""
        # Route to appropriate handler based on task type
        handlers = {
            "planning_session": self._handle_planning_task,
            "agent_execution": self._handle_agent_task,
            "llm_call": self._handle_llm_task,
        }
        
        handler = handlers.get(task.type)
        if not handler:
            raise ValueError(f"Unknown task type: {task.type}")
        
        await asyncio.wait_for(
            handler(task),
            timeout=self.config["task_timeout"] / 1000,
        )
    
    async def _handle_task_failure(self, task: TaskInfo, error: str):
        """Handle task failure with retry logic"""
        if task.attempts < self.config["max_task_retries"]:
            # Re-queue for retry
            task.status = "pending"
            await self.task_queue.put(task.id)
            logger.warning(f"Task {task.id} failed ({error}), retrying (attempt {task.attempts})")
        else:
            task.status = "failed"
            logger.error(f"Task {task.id} failed permanently after {task.attempts} attempts: {error}")
    
    async def _health_check_loop(self):
        """Periodic health check of workers"""
        while self._running:
            await asyncio.sleep(self.config["health_check_interval"] / 1000)
            
            for worker_id, worker in list(self.workers.items()):
                # Check worker lifetime
                lifetime = (datetime.utcnow() - worker.started_at).total_seconds() * 1000
                
                if lifetime > self.config["worker_max_lifetime"]:
                    logger.info(f"Worker {worker_id} reached max lifetime, recycling")
                    await self._stop_worker(worker_id)
                    await self._spawn_worker()
    
    async def _scaling_loop(self):
        """Auto-scale workers based on queue depth"""
        while self._running:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            queue_depth = self.task_queue.qsize()
            active_workers = len([w for w in self.workers.values() if w.status != "stopping"])
            idle_workers = len([w for w in self.workers.values() if w.status == "idle"])
            
            # Scale up if queue is deep and we have capacity
            if (
                queue_depth > self.config["target_queue_depth"]
                and active_workers < self.config["max_workers"]
            ):
                workers_needed = min(
                    queue_depth - idle_workers,
                    self.config["max_workers"] - active_workers,
                )
                
                for _ in range(workers_needed):
                    await self._spawn_worker()
                
                logger.info(f"Scaled up by {workers_needed} workers, total: {len(self.workers)}")
            
            # Scale down if too many idle workers
            elif (
                idle_workers > 2
                and active_workers > self.config["min_workers"]
            ):
                # Stop one idle worker
                for worker_id, worker in self.workers.items():
                    if worker.status == "idle":
                        await self._stop_worker(worker_id)
                        break
                
                logger.info(f"Scaled down, total workers: {len(self.workers)}")
    
    async def _dispatch_loop(self):
        """Monitor and log dispatch metrics"""
        while self._running:
            await asyncio.sleep(60)  # Log every minute
            
            stats = {
                "workers": len(self.workers),
                "idle": len([w for w in self.workers.values() if w.status == "idle"]),
                "busy": len([w for w in self.workers.values() if w.status == "busy"]),
                "queue_depth": self.task_queue.qsize(),
                "tasks_total": len(self.tasks),
                "tasks_completed": len([t for t in self.tasks.values() if t.status == "completed"]),
                "tasks_failed": len([t for t in self.tasks.values() if t.status == "failed"]),
            }
            
            logger.info(f"Worker stats: {stats}")
    
    # Task handlers (to be implemented)
    
    async def _handle_planning_task(self, task: TaskInfo):
        """Handle planning session task"""
        from .cortex import CortexAgent
        # Implementation...
        pass
    
    async def _handle_agent_task(self, task: TaskInfo):
        """Handle agent execution task"""
        pass
    
    async def _handle_llm_task(self, task: TaskInfo):
        """Handle direct LLM call task"""
        pass
```

### 3.3 Task Queue Schema (RabbitMQ)

```typescript
// Queue configuration
const QUEUE_CONFIG = {
  // Main task queue
  tasks: {
    name: 'forgeagents.tasks',
    durable: true,
    arguments: {
      'x-message-ttl': 86400000,  // 24 hours
      'x-dead-letter-exchange': 'forgeagents.dlx',
      'x-dead-letter-routing-key': 'failed',
    },
  },
  
  // Priority queues
  tasksPriority: {
    name: 'forgeagents.tasks.priority',
    durable: true,
    arguments: {
      'x-max-priority': 10,
      'x-message-ttl': 3600000,  // 1 hour
    },
  },
  
  // Dead letter queue
  dlq: {
    name: 'forgeagents.dlq',
    durable: true,
  },
  
  // Events for SSE
  events: {
    name: 'forgeagents.events',
    durable: false,
    arguments: {
      'x-message-ttl': 300000,  // 5 minutes
    },
  },
};

// Message schema
interface TaskMessage {
  id: string;
  type: string;
  priority: number;
  payload: Record<string, unknown>;
  metadata: {
    userId: string;
    correlationId: string;
    timestamp: string;
    attempts: number;
    maxAttempts: number;
    timeout: number;
  };
}
```

---

## 4. License Enforcement Hooks

### 4.1 Enforcement Points

```typescript
/**
 * License enforcement happens at these points:
 * 
 * 1. API Gateway - Initial request validation
 * 2. ForgeAgents - Before agent/session creation
 * 3. ForgeAgents - During execution (quota tracking)
 * 4. NeuroForge - Before LLM calls (cost limits)
 */

// Enforcement hook interface
interface LicenseEnforcement {
  // Check before action
  canPerform(action: string, context: EnforcementContext): Promise<EnforcementResult>;
  
  // Track usage after action
  trackUsage(action: string, usage: UsageRecord): Promise<void>;
  
  // Get current limits
  getLimits(userId: string): Promise<UserLimits>;
}

interface EnforcementContext {
  userId: string;
  action: string;
  resource?: string;
  estimatedCost?: number;
  estimatedTokens?: number;
}

interface EnforcementResult {
  allowed: boolean;
  reason?: string;
  limitType?: string;
  current?: number;
  limit?: number;
  upgradeUrl?: string;
}
```

### 4.2 Enforcement Implementation

```python
# forgeagents/license/enforcement.py

from typing import Optional
from dataclasses import dataclass
from enum import Enum


class EnforcementPoint(Enum):
    # Pre-execution checks
    CREATE_AGENT = "create_agent"
    START_AGENT = "start_agent"
    CREATE_PLANNING_SESSION = "create_planning_session"
    CONNECT_SSE = "connect_sse"
    
    # During execution
    LLM_CALL = "llm_call"
    TOOL_EXECUTION = "tool_execution"
    FILE_OPERATION = "file_operation"


@dataclass
class EnforcementRule:
    point: EnforcementPoint
    feature: str
    limit_key: str
    check_quota: bool = True
    check_feature: bool = True
    check_concurrency: bool = False
    estimated_cost_key: Optional[str] = None


ENFORCEMENT_RULES = {
    EnforcementPoint.CREATE_AGENT: EnforcementRule(
        point=EnforcementPoint.CREATE_AGENT,
        feature="agents.basic",
        limit_key="agents_per_day",
        check_quota=True,
        check_feature=True,
    ),
    EnforcementPoint.START_AGENT: EnforcementRule(
        point=EnforcementPoint.START_AGENT,
        feature="agents.basic",
        limit_key="concurrent_agents",
        check_concurrency=True,
    ),
    EnforcementPoint.CREATE_PLANNING_SESSION: EnforcementRule(
        point=EnforcementPoint.CREATE_PLANNING_SESSION,
        feature="cortex.multi_ai",
        limit_key="planning_sessions_per_month",
        check_quota=True,
        check_feature=True,
        check_concurrency=True,
        estimated_cost_key="max_cost_per_session",
    ),
    EnforcementPoint.CONNECT_SSE: EnforcementRule(
        point=EnforcementPoint.CONNECT_SSE,
        feature=None,  # No feature required
        limit_key="sse_connections",
        check_concurrency=True,
    ),
    EnforcementPoint.LLM_CALL: EnforcementRule(
        point=EnforcementPoint.LLM_CALL,
        feature=None,
        limit_key="tokens_per_day",
        check_quota=True,
        estimated_cost_key="max_cost_per_call",
    ),
}


class LicenseEnforcer:
    """Centralized license enforcement"""
    
    def __init__(self, license_service, usage_service, concurrency_manager):
        self.license_service = license_service
        self.usage_service = usage_service
        self.concurrency_manager = concurrency_manager
    
    async def enforce(
        self,
        point: EnforcementPoint,
        user_id: str,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Enforce license at the given point.
        
        Returns:
            {
                "allowed": bool,
                "reason": str | None,
                "details": dict | None
            }
        """
        rule = ENFORCEMENT_RULES.get(point)
        if not rule:
            return {"allowed": True}
        
        # Get user's license
        license = await self.license_service.get_license(user_id)
        
        # 1. Check feature access
        if rule.check_feature and rule.feature:
            if not self._has_feature(license, rule.feature):
                return {
                    "allowed": False,
                    "reason": "feature_not_available",
                    "details": {
                        "feature": rule.feature,
                        "tier": license.tier,
                        "upgrade_url": f"/upgrade?feature={rule.feature}",
                    }
                }
        
        # 2. Check quota
        if rule.check_quota:
            usage = await self.usage_service.get_usage(user_id, rule.limit_key)
            limit = self._get_limit(license, rule.limit_key)
            
            if limit != -1 and usage >= limit:
                return {
                    "allowed": False,
                    "reason": "quota_exceeded",
                    "details": {
                        "limit_type": rule.limit_key,
                        "used": usage,
                        "limit": limit,
                        "resets_at": self._get_reset_time(rule.limit_key),
                    }
                }
        
        # 3. Check concurrency
        if rule.check_concurrency:
            result = await self.concurrency_manager.check(
                user_id,
                rule.limit_key,
                license.tier,
            )
            
            if not result.allowed:
                return {
                    "allowed": False,
                    "reason": "concurrency_limit",
                    "details": {
                        "limit_type": rule.limit_key,
                        "current": result.current,
                        "limit": result.limit,
                    }
                }
        
        # 4. Check estimated cost (if applicable)
        if rule.estimated_cost_key and context:
            estimated_cost = context.get("estimated_cost", 0)
            max_cost = self._get_limit(license, rule.estimated_cost_key)
            
            if max_cost != -1 and estimated_cost > max_cost:
                return {
                    "allowed": False,
                    "reason": "cost_limit_exceeded",
                    "details": {
                        "estimated_cost": estimated_cost,
                        "max_cost": max_cost,
                    }
                }
        
        return {"allowed": True}
    
    async def track(
        self,
        point: EnforcementPoint,
        user_id: str,
        usage: dict,
    ):
        """Track usage after action completes"""
        rule = ENFORCEMENT_RULES.get(point)
        if not rule or not rule.check_quota:
            return
        
        await self.usage_service.record_usage(
            user_id=user_id,
            limit_key=rule.limit_key,
            amount=usage.get("amount", 1),
            metadata=usage,
        )
    
    def _has_feature(self, license, feature: str) -> bool:
        return feature in license.features
    
    def _get_limit(self, license, limit_key: str) -> int:
        return license.limits.get(limit_key, 0)
    
    def _get_reset_time(self, limit_key: str) -> str:
        # Return next reset time based on limit type
        from datetime import datetime, timedelta
        
        if "per_day" in limit_key:
            tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0) + timedelta(days=1)
            return tomorrow.isoformat()
        elif "per_month" in limit_key:
            next_month = datetime.utcnow().replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1, hour=0, minute=0, second=0)
            return next_month.isoformat()
        
        return None
```

### 4.3 Integration with Cortex

```python
# forgeagents/cortex/routes.py

from fastapi import APIRouter, Depends, HTTPException
from ..license.enforcement import LicenseEnforcer, EnforcementPoint

router = APIRouter()


@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    enforcer: LicenseEnforcer = Depends(get_enforcer),
):
    # 1. Estimate cost
    cost_estimate = await estimate_session_cost(request)
    
    # 2. Enforce license
    result = await enforcer.enforce(
        EnforcementPoint.CREATE_PLANNING_SESSION,
        user_id,
        context={"estimated_cost": cost_estimate.max_cost},
    )
    
    if not result["allowed"]:
        raise HTTPException(
            status_code=402 if result["reason"] == "quota_exceeded" else 403,
            detail=result,
        )
    
    # 3. Acquire concurrency slot
    slot = await enforcer.concurrency_manager.acquire(
        user_id,
        "planning_session",
    )
    
    if not slot.acquired:
        raise HTTPException(
            status_code=429,
            detail={
                "reason": "concurrency_limit",
                "current": slot.current,
                "limit": slot.limit,
            }
        )
    
    try:
        # 4. Create session
        session = await create_planning_session(request, user_id)
        
        # 5. Track usage (initial)
        await enforcer.track(
            EnforcementPoint.CREATE_PLANNING_SESSION,
            user_id,
            {"session_id": session.id, "amount": 1},
        )
        
        return session
    
    except Exception:
        # Release slot on failure
        await enforcer.concurrency_manager.release(user_id, "planning_session")
        raise
```

---

## 5. NeuroForge Routing Logic

### 5.1 Cost-Based Model Selection

```python
# neuroforge/routing/cost_router.py

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class TaskComplexity(Enum):
    LOW = "low"       # Simple queries, short outputs
    MEDIUM = "medium" # Standard tasks
    HIGH = "high"     # Complex reasoning, long outputs


@dataclass
class ModelCost:
    provider: str
    model: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    context_window: int
    max_output: int
    
    # Performance characteristics
    avg_latency_ms: int
    reliability_score: float  # 0-1
    quality_score: float      # 0-1 for task type


@dataclass
class RoutingConstraints:
    max_cost: Optional[float] = None
    max_latency_ms: Optional[int] = None
    min_quality: Optional[float] = None
    preferred_providers: Optional[List[str]] = None
    excluded_models: Optional[List[str]] = None


class CostAwareRouter:
    """Routes requests to optimal model based on cost, latency, and quality"""
    
    def __init__(self, model_registry: "ModelRegistry"):
        self.registry = model_registry
    
    def route(
        self,
        task_type: str,
        complexity: TaskComplexity,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        constraints: RoutingConstraints,
    ) -> "RoutingDecision":
        """
        Select optimal model based on:
        1. Task requirements
        2. Cost constraints
        3. Latency requirements
        4. Quality expectations
        """
        
        # Get all available models
        candidates = self.registry.get_available_models()
        
        # Filter by constraints
        candidates = self._filter_candidates(
            candidates,
            constraints,
            estimated_input_tokens,
            estimated_output_tokens,
        )
        
        if not candidates:
            raise NoSuitableModelError("No models match constraints")
        
        # Score each candidate
        scored = []
        for model in candidates:
            score = self._score_model(
                model,
                task_type,
                complexity,
                estimated_input_tokens,
                estimated_output_tokens,
                constraints,
            )
            scored.append((model, score))
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Select primary and fallbacks
        primary = scored[0][0]
        fallbacks = [m for m, _ in scored[1:4]]  # Top 3 fallbacks
        
        return RoutingDecision(
            primary_model=primary,
            fallback_models=fallbacks,
            estimated_cost=self._calculate_cost(
                primary,
                estimated_input_tokens,
                estimated_output_tokens,
            ),
            estimated_latency=primary.avg_latency_ms,
            reasoning=self._generate_reasoning(primary, constraints),
        )
    
    def _filter_candidates(
        self,
        models: List[ModelCost],
        constraints: RoutingConstraints,
        input_tokens: int,
        output_tokens: int,
    ) -> List[ModelCost]:
        """Filter models by hard constraints"""
        result = []
        
        for model in models:
            # Check context window
            if input_tokens > model.context_window:
                continue
            
            # Check output capacity
            if output_tokens > model.max_output:
                continue
            
            # Check cost constraint
            if constraints.max_cost:
                cost = self._calculate_cost(model, input_tokens, output_tokens)
                if cost > constraints.max_cost:
                    continue
            
            # Check latency constraint
            if constraints.max_latency_ms:
                if model.avg_latency_ms > constraints.max_latency_ms:
                    continue
            
            # Check quality constraint
            if constraints.min_quality:
                if model.quality_score < constraints.min_quality:
                    continue
            
            # Check provider preferences
            if constraints.preferred_providers:
                if model.provider not in constraints.preferred_providers:
                    continue
            
            # Check exclusions
            if constraints.excluded_models:
                if model.model in constraints.excluded_models:
                    continue
            
            result.append(model)
        
        return result
    
    def _score_model(
        self,
        model: ModelCost,
        task_type: str,
        complexity: TaskComplexity,
        input_tokens: int,
        output_tokens: int,
        constraints: RoutingConstraints,
    ) -> float:
        """
        Score model on scale of 0-100.
        
        Weights:
        - Quality: 40%
        - Cost efficiency: 30%
        - Reliability: 20%
        - Latency: 10%
        """
        
        # Quality score (0-40)
        quality_weight = 40
        quality_score = model.quality_score * quality_weight
        
        # Adjust for task complexity
        if complexity == TaskComplexity.HIGH:
            # Prefer higher quality for complex tasks
            quality_score *= 1.2
        elif complexity == TaskComplexity.LOW:
            # Lower weight for simple tasks
            quality_score *= 0.8
        
        # Cost efficiency score (0-30)
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        max_cost = constraints.max_cost or 1.0
        cost_efficiency = max(0, 1 - (cost / max_cost))
        cost_score = cost_efficiency * 30
        
        # Reliability score (0-20)
        reliability_score = model.reliability_score * 20
        
        # Latency score (0-10)
        max_latency = constraints.max_latency_ms or 10000
        latency_efficiency = max(0, 1 - (model.avg_latency_ms / max_latency))
        latency_score = latency_efficiency * 10
        
        return quality_score + cost_score + reliability_score + latency_score
    
    def _calculate_cost(
        self,
        model: ModelCost,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate estimated cost for a model"""
        input_cost = (input_tokens / 1000) * model.input_cost_per_1k
        output_cost = (output_tokens / 1000) * model.output_cost_per_1k
        return input_cost + output_cost
    
    def _generate_reasoning(
        self,
        model: ModelCost,
        constraints: RoutingConstraints,
    ) -> str:
        """Generate human-readable reasoning for selection"""
        reasons = []
        
        reasons.append(f"Selected {model.provider}/{model.model}")
        reasons.append(f"Quality score: {model.quality_score:.2f}")
        reasons.append(f"Avg latency: {model.avg_latency_ms}ms")
        reasons.append(f"Reliability: {model.reliability_score:.2f}")
        
        if constraints.preferred_providers:
            if model.provider in constraints.preferred_providers:
                reasons.append("Matches preferred provider")
        
        return "; ".join(reasons)


@dataclass
class RoutingDecision:
    primary_model: ModelCost
    fallback_models: List[ModelCost]
    estimated_cost: float
    estimated_latency: int
    reasoning: str
```

### 5.2 Dynamic Model Registry

```python
# neuroforge/routing/registry.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import httpx


@dataclass
class ModelHealth:
    is_available: bool
    last_check: datetime
    error_rate: float       # 0-1
    avg_latency_ms: float
    last_error: Optional[str] = None


@dataclass 
class RegisteredModel:
    provider: str
    model_id: str
    display_name: str
    
    # Capabilities
    context_window: int
    max_output_tokens: int
    supports_streaming: bool
    supports_tools: bool
    supports_vision: bool
    
    # Costs (USD)
    input_cost_per_1k: float
    output_cost_per_1k: float
    
    # Quality scores by task type (0-1)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    
    # Runtime state
    health: ModelHealth = field(default_factory=lambda: ModelHealth(
        is_available=True,
        last_check=datetime.utcnow(),
        error_rate=0,
        avg_latency_ms=1000,
    ))
    
    # Metadata
    added_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


class ModelRegistry:
    """Dynamic registry of available models with health tracking"""
    
    def __init__(self):
        self._models: Dict[str, RegisteredModel] = {}
        self._health_check_interval = 60  # seconds
        self._error_window = 100  # last N requests for error rate
        self._request_history: Dict[str, List[bool]] = {}  # model_id -> [success/fail]
    
    async def start(self):
        """Start background health checks"""
        asyncio.create_task(self._health_check_loop())
    
    def register_model(self, model: RegisteredModel):
        """Register a new model"""
        key = f"{model.provider}/{model.model_id}"
        self._models[key] = model
        self._request_history[key] = []
    
    def get_model(self, provider: str, model_id: str) -> Optional[RegisteredModel]:
        """Get a specific model"""
        return self._models.get(f"{provider}/{model_id}")
    
    def get_available_models(self) -> List[RegisteredModel]:
        """Get all available models"""
        return [m for m in self._models.values() if m.health.is_available]
    
    def get_models_by_capability(self, capability: str) -> List[RegisteredModel]:
        """Get models that support a capability"""
        capability_map = {
            "streaming": lambda m: m.supports_streaming,
            "tools": lambda m: m.supports_tools,
            "vision": lambda m: m.supports_vision,
        }
        
        filter_fn = capability_map.get(capability)
        if not filter_fn:
            return self.get_available_models()
        
        return [m for m in self.get_available_models() if filter_fn(m)]
    
    def record_request(
        self,
        provider: str,
        model_id: str,
        success: bool,
        latency_ms: float,
        error: Optional[str] = None,
    ):
        """Record request outcome for health tracking"""
        key = f"{provider}/{model_id}"
        model = self._models.get(key)
        
        if not model:
            return
        
        # Update request history
        history = self._request_history.get(key, [])
        history.append(success)
        if len(history) > self._error_window:
            history = history[-self._error_window:]
        self._request_history[key] = history
        
        # Update error rate
        if history:
            model.health.error_rate = 1 - (sum(history) / len(history))
        
        # Update latency (exponential moving average)
        alpha = 0.1
        model.health.avg_latency_ms = (
            alpha * latency_ms + 
            (1 - alpha) * model.health.avg_latency_ms
        )
        
        # Update last error
        if not success and error:
            model.health.last_error = error
        
        # Update last used
        model.last_used = datetime.utcnow()
        
        # Check if model should be marked unavailable
        if model.health.error_rate > 0.5:  # >50% errors
            model.health.is_available = False
    
    async def _health_check_loop(self):
        """Periodic health check of all models"""
        while True:
            await asyncio.sleep(self._health_check_interval)
            
            for key, model in self._models.items():
                try:
                    is_healthy = await self._check_model_health(model)
                    model.health.is_available = is_healthy
                    model.health.last_check = datetime.utcnow()
                    
                    # Reset error rate if model recovered
                    if is_healthy and model.health.error_rate > 0.3:
                        model.health.error_rate *= 0.8
                
                except Exception as e:
                    model.health.is_available = False
                    model.health.last_error = str(e)
    
    async def _check_model_health(self, model: RegisteredModel) -> bool:
        """Check if a model is healthy"""
        # Provider-specific health checks
        health_checks = {
            "openai": self._check_openai_health,
            "anthropic": self._check_anthropic_health,
            "xai": self._check_xai_health,
            "google": self._check_google_health,
        }
        
        check_fn = health_checks.get(model.provider)
        if not check_fn:
            return True  # Assume healthy if no check
        
        return await check_fn(model.model_id)
    
    async def _check_openai_health(self, model_id: str) -> bool:
        """Check OpenAI model availability"""
        # Could hit /models endpoint or do lightweight completion
        # For now, assume available
        return True
    
    async def _check_anthropic_health(self, model_id: str) -> bool:
        return True
    
    async def _check_xai_health(self, model_id: str) -> bool:
        return True
    
    async def _check_google_health(self, model_id: str) -> bool:
        return True


# Default model configuration
DEFAULT_MODELS = [
    RegisteredModel(
        provider="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        context_window=128000,
        max_output_tokens=16384,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        quality_scores={
            "chat": 0.95,
            "code": 0.90,
            "analysis": 0.92,
            "creative": 0.88,
            "planning": 0.90,
        },
    ),
    RegisteredModel(
        provider="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        context_window=128000,
        max_output_tokens=16384,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        input_cost_per_1k=0.00015,
        output_cost_per_1k=0.0006,
        quality_scores={
            "chat": 0.85,
            "code": 0.80,
            "analysis": 0.82,
            "creative": 0.78,
            "planning": 0.75,
        },
    ),
    RegisteredModel(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        context_window=200000,
        max_output_tokens=8192,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
        quality_scores={
            "chat": 0.94,
            "code": 0.95,
            "analysis": 0.96,
            "creative": 0.92,
            "planning": 0.95,
        },
    ),
    RegisteredModel(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5",
        context_window=200000,
        max_output_tokens=8192,
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        input_cost_per_1k=0.0008,
        output_cost_per_1k=0.004,
        quality_scores={
            "chat": 0.82,
            "code": 0.80,
            "analysis": 0.80,
            "creative": 0.78,
            "planning": 0.75,
        },
    ),
    RegisteredModel(
        provider="xai",
        model_id="grok-2",
        display_name="Grok 2",
        context_window=128000,
        max_output_tokens=8192,
        supports_streaming=True,
        supports_tools=False,
        supports_vision=False,
        input_cost_per_1k=0.002,
        output_cost_per_1k=0.010,
        quality_scores={
            "chat": 0.88,
            "code": 0.82,
            "analysis": 0.85,
            "creative": 0.90,
            "planning": 0.82,
        },
    ),
]
```

---

## 6. DataForge Storage Schemas

### 6.1 Core Tables

```sql
-- DataForge PostgreSQL Schema
-- Version: 1.0

-- =====================================================
-- USERS & ORGANIZATIONS
-- =====================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255),
    display_name VARCHAR(255),
    avatar_url VARCHAR(500),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);


-- =====================================================
-- LICENSES
-- =====================================================

CREATE TABLE licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    
    -- Tier & Status
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    
    -- Validity
    activated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    
    -- Features & Limits
    features TEXT[] DEFAULT '{}',
    limits JSONB DEFAULT '{}',
    
    -- Devices
    max_devices INTEGER DEFAULT 3,
    
    -- Billing
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    
    -- Metadata
    source VARCHAR(50) DEFAULT 'signup',
    coupon_code VARCHAR(100),
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_licenses_user ON licenses(user_id);
CREATE INDEX idx_licenses_status ON licenses(status);
CREATE INDEX idx_licenses_tier ON licenses(tier);

CREATE TABLE license_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    fingerprint VARCHAR(255) NOT NULL,
    
    is_active BOOLEAN DEFAULT TRUE,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(license_id, fingerprint)
);

CREATE INDEX idx_license_devices_license ON license_devices(license_id);


-- =====================================================
-- USAGE TRACKING
-- =====================================================

CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- What was used
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    
    -- Usage details
    metric VARCHAR(100) NOT NULL,
    amount DECIMAL(15, 6) NOT NULL,
    
    -- Period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_user_period ON usage_records(user_id, period_start, period_end);
CREATE INDEX idx_usage_resource ON usage_records(resource_type, resource_id);
CREATE INDEX idx_usage_metric ON usage_records(user_id, metric, period_start);

-- Aggregated usage view
CREATE VIEW usage_summary AS
SELECT 
    user_id,
    metric,
    DATE_TRUNC('day', period_start) as day,
    SUM(amount) as total_amount
FROM usage_records
GROUP BY user_id, metric, DATE_TRUNC('day', period_start);


-- =====================================================
-- AGENTS
-- =====================================================

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Definition
    type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Configuration
    config JSONB DEFAULT '{}',
    policy JSONB DEFAULT '{}',
    
    -- State
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    error_message TEXT,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Metrics
    metrics JSONB DEFAULT '{}'
);

CREATE INDEX idx_agents_user ON agents(user_id);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_type ON agents(type);
CREATE INDEX idx_agents_created ON agents(created_at DESC);


-- =====================================================
-- TASKS
-- =====================================================

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES tasks(id),
    
    -- Definition
    type VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Input/Output
    input JSONB DEFAULT '{}',
    output JSONB,
    
    -- Execution
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 1,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Error
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Dependencies
    depends_on UUID[] DEFAULT '{}'
);

CREATE INDEX idx_tasks_agent ON tasks(agent_id);
CREATE INDEX idx_tasks_status ON tasks(agent_id, status);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);


-- =====================================================
-- PLANNING SESSIONS (CORTEX)
-- =====================================================

CREATE TABLE planning_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),
    
    -- Request
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    context TEXT,
    
    -- Configuration
    pipeline VARCHAR(50) NOT NULL DEFAULT 'default',
    config JSONB DEFAULT '{}',
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    current_stage_index INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Results
    final_plan JSONB,
    
    -- Metrics
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_planning_sessions_user ON planning_sessions(user_id);
CREATE INDEX idx_planning_sessions_status ON planning_sessions(status);
CREATE INDEX idx_planning_sessions_created ON planning_sessions(created_at DESC);

CREATE TABLE planning_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES planning_sessions(id) ON DELETE CASCADE,
    
    -- Stage info
    stage_index INTEGER NOT NULL,
    stage_type VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    
    -- Execution
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    prompt TEXT,
    output TEXT,
    summary TEXT,
    
    -- Metrics
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    
    -- User intervention
    user_injection TEXT,
    was_restarted BOOLEAN DEFAULT FALSE,
    
    -- Error
    error_message TEXT,
    error_code VARCHAR(50),
    
    UNIQUE(session_id, stage_index)
);

CREATE INDEX idx_planning_stages_session ON planning_stages(session_id);


-- =====================================================
-- AGENT MEMORY
-- =====================================================

CREATE TABLE agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Memory type
    memory_type VARCHAR(50) NOT NULL, -- short_term, long_term, episodic
    
    -- Content
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    
    -- Vector embedding (for semantic search)
    embedding vector(1536),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    UNIQUE(agent_id, memory_type, key)
);

CREATE INDEX idx_agent_memories_agent ON agent_memories(agent_id);
CREATE INDEX idx_agent_memories_type ON agent_memories(agent_id, memory_type);
CREATE INDEX idx_agent_memories_embedding ON agent_memories USING ivfflat (embedding vector_cosine_ops);


-- =====================================================
-- AUDIT LOG
-- =====================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Who
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    
    -- What
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    
    -- Result
    status VARCHAR(50) NOT NULL, -- success, failure
    error_message TEXT,
    
    -- Details
    details JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- Partition audit logs by month for performance
-- CREATE TABLE audit_logs_2025_12 PARTITION OF audit_logs
--     FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');


-- =====================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================

-- Updated at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER licenses_updated_at
    BEFORE UPDATE ON licenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- =====================================================
-- INDEXES FOR COMMON QUERIES
-- =====================================================

-- Active agents by user
CREATE INDEX idx_agents_user_active ON agents(user_id) 
    WHERE status IN ('running', 'paused');

-- Recent planning sessions
CREATE INDEX idx_planning_recent ON planning_sessions(user_id, created_at DESC)
    WHERE status != 'deleted';

-- Usage for current month
CREATE INDEX idx_usage_current_month ON usage_records(user_id, metric)
    WHERE period_start >= DATE_TRUNC('month', NOW());
```

### 6.2 Redis Cache Schema

```typescript
// Redis key patterns and TTLs

const REDIS_KEYS = {
  // Session tokens
  'session:{userId}:{sessionId}': {
    type: 'hash',
    ttl: 86400,  // 24 hours
    fields: ['accessToken', 'refreshToken', 'deviceId', 'createdAt'],
  },
  
  // License cache
  'license:{userId}': {
    type: 'hash',
    ttl: 3600,  // 1 hour
    fields: ['tier', 'status', 'features', 'limits', 'expiresAt'],
  },
  
  // Usage counters
  'usage:{userId}:{metric}:{period}': {
    type: 'string',
    ttl: 86400 * 32,  // 32 days
    value: 'integer',
  },
  
  // Concurrency tracking
  'concurrency:{userId}:{resourceType}': {
    type: 'string',
    ttl: 86400,
    value: 'integer',
  },
  
  // Rate limiting
  'ratelimit:{userId}:{endpoint}:{window}': {
    type: 'string',
    ttl: 'dynamic',  // Based on window size
    value: 'integer',
  },
  
  // Agent state cache
  'agent:{agentId}:state': {
    type: 'hash',
    ttl: 3600,
    fields: ['status', 'currentTaskId', 'progress', 'updatedAt'],
  },
  
  // SSE session state
  'sse:{sessionId}': {
    type: 'hash',
    ttl: 86400,
    fields: ['lastEventId', 'status', 'createdAt'],
  },
  
  // Model health cache
  'model:{provider}:{modelId}:health': {
    type: 'hash',
    ttl: 60,  // 1 minute
    fields: ['isAvailable', 'errorRate', 'avgLatency', 'lastCheck'],
  },
};
```

---

## 7. Multi-Tenant Isolation

### 7.1 Isolation Levels

```typescript
/**
 * Multi-tenant isolation strategy
 * 
 * Level 1: Shared Everything (Current - Free/Trial)
 * - Same database, same tables
 * - Row-level security via user_id/org_id
 * 
 * Level 2: Shared Database, Separate Schemas (Pro)
 * - Same database
 * - Per-organization schema
 * - Better isolation, same infrastructure
 * 
 * Level 3: Dedicated Database (Enterprise)
 * - Separate database per organization
 * - Full isolation
 * - Custom retention, compliance
 */

type IsolationLevel = 'shared' | 'schema' | 'dedicated';

interface TenantConfig {
  organizationId: string;
  isolationLevel: IsolationLevel;
  
  // Database
  databaseUrl?: string;  // For dedicated
  schemaName?: string;   // For schema isolation
  
  // Resources
  dedicatedWorkers?: number;
  maxConcurrentAgents?: number;
  
  // Compliance
  dataRegion?: string;
  retentionDays?: number;
  encryptionKey?: string;
}
```

### 7.2 Row-Level Security (Shared Model)

```sql
-- Enable RLS on all tenant tables
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE planning_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own data
CREATE POLICY user_isolation ON agents
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::uuid);

CREATE POLICY user_isolation ON tasks
    FOR ALL
    USING (
        agent_id IN (
            SELECT id FROM agents 
            WHERE user_id = current_setting('app.current_user_id')::uuid
        )
    );

CREATE POLICY user_isolation ON planning_sessions
    FOR ALL
    USING (user_id = current_setting('app.current_user_id')::uuid);

-- Policy: Organization members can see org data
CREATE POLICY org_isolation ON agents
    FOR SELECT
    USING (
        user_id IN (
            SELECT id FROM users 
            WHERE organization_id = current_setting('app.current_org_id')::uuid
        )
    );

-- Set context in each request
-- SET app.current_user_id = 'user-uuid';
-- SET app.current_org_id = 'org-uuid';
```

### 7.3 Request Context

```python
# forgeagents/middleware/tenant.py

from fastapi import Request
from contextvars import ContextVar

# Context variables for current tenant
current_user_id: ContextVar[str] = ContextVar('current_user_id')
current_org_id: ContextVar[str] = ContextVar('current_org_id')
current_tenant_config: ContextVar[dict] = ContextVar('current_tenant_config')


class TenantMiddleware:
    """Sets tenant context for each request"""
    
    async def __call__(self, request: Request, call_next):
        # Extract from JWT
        user_id = request.state.user_id
        org_id = request.state.org_id
        
        # Set context vars
        current_user_id.set(user_id)
        current_org_id.set(org_id)
        
        # Load tenant config
        config = await self.load_tenant_config(org_id)
        current_tenant_config.set(config)
        
        # Set database context (for RLS)
        await self.set_db_context(user_id, org_id)
        
        response = await call_next(request)
        
        return response
    
    async def set_db_context(self, user_id: str, org_id: str):
        """Set PostgreSQL session variables for RLS"""
        from ..database import get_db
        
        async with get_db() as db:
            await db.execute(f"SET app.current_user_id = '{user_id}'")
            if org_id:
                await db.execute(f"SET app.current_org_id = '{org_id}'")
```

---

## 8. API Route Reconciliation

### 8.1 Canonical Endpoint List

This is the authoritative list of all ForgeAgents API endpoints. Any implementation must match exactly.

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| **Authentication** ||||
| POST | `/api/v1/auth/login` | Login | No |
| POST | `/api/v1/auth/refresh` | Refresh token | No |
| POST | `/api/v1/auth/logout` | Logout | Yes |
| **License** ||||
| GET | `/api/v1/license` | Get current license | Yes |
| POST | `/api/v1/license/verify` | Verify feature access | Yes |
| GET | `/api/v1/license/usage` | Get usage for period | Yes |
| **Agents** ||||
| GET | `/api/v1/agents` | List agents | Yes |
| POST | `/api/v1/agents` | Create agent | Yes |
| GET | `/api/v1/agents/{id}` | Get agent | Yes |
| DELETE | `/api/v1/agents/{id}` | Delete agent | Yes |
| POST | `/api/v1/agents/{id}/start` | Start agent | Yes |
| POST | `/api/v1/agents/{id}/pause` | Pause agent | Yes |
| POST | `/api/v1/agents/{id}/resume` | Resume agent | Yes |
| POST | `/api/v1/agents/{id}/cancel` | Cancel agent | Yes |
| GET | `/api/v1/agents/{id}/events` | SSE stream | Yes |
| **Tasks** ||||
| GET | `/api/v1/agents/{id}/tasks` | List tasks | Yes |
| POST | `/api/v1/agents/{id}/tasks` | Create task | Yes |
| GET | `/api/v1/agents/{id}/tasks/{taskId}` | Get task | Yes |
| GET | `/api/v1/agents/{id}/tasks/{taskId}/output` | Get output | Yes |
| **Cortex** ||||
| GET | `/api/v1/cortex/pipelines` | List pipelines | Yes |
| GET | `/api/v1/cortex/pipelines/{name}` | Get pipeline | Yes |
| POST | `/api/v1/cortex/estimate` | Estimate cost | Yes |
| POST | `/api/v1/cortex/sessions` | Create session | Yes |
| POST | `/api/v1/cortex/sessions/stream` | Create + stream | Yes |
| GET | `/api/v1/cortex/sessions/{id}` | Get session | Yes |
| GET | `/api/v1/cortex/sessions/{id}/stages` | Get stages | Yes |
| GET | `/api/v1/cortex/sessions/{id}/stages/{idx}/output` | Get stage output | Yes |
| GET | `/api/v1/cortex/sessions/{id}/deliverable` | Get deliverable | Yes |
| POST | `/api/v1/cortex/sessions/{id}/pause` | Pause | Yes |
| POST | `/api/v1/cortex/sessions/{id}/resume` | Resume | Yes |
| POST | `/api/v1/cortex/sessions/{id}/abort` | Abort | Yes |
| POST | `/api/v1/cortex/sessions/{id}/inject` | Inject context | Yes |
| **Health** ||||
| GET | `/health` | Health check | No |
| GET | `/health/live` | Liveness | No |
| GET | `/health/ready` | Readiness | No |

### 8.2 Client SDK Methods

```typescript
// VibeForge client must implement these methods

interface ForgeAgentsClient {
  // Auth
  login(email: string, password: string): Promise<AuthResponse>;
  logout(): Promise<void>;
  refreshToken(): Promise<void>;
  
  // License
  getLicense(): Promise<License>;
  verifyFeature(feature: string): Promise<VerifyResult>;
  getUsage(): Promise<UsageReport>;
  
  // Agents
  listAgents(filters?: AgentFilters): Promise<AgentList>;
  createAgent(request: CreateAgentRequest): Promise<Agent>;
  getAgent(id: string): Promise<Agent>;
  deleteAgent(id: string): Promise<void>;
  startAgent(id: string): Promise<Agent>;
  pauseAgent(id: string): Promise<void>;
  resumeAgent(id: string, context?: string): Promise<void>;
  cancelAgent(id: string, reason?: string): Promise<void>;
  streamAgentEvents(id: string, handlers: SSEHandlers): () => void;
  
  // Tasks
  listTasks(agentId: string): Promise<Task[]>;
  createTask(agentId: string, request: CreateTaskRequest): Promise<Task>;
  getTask(agentId: string, taskId: string): Promise<Task>;
  getTaskOutput(agentId: string, taskId: string): Promise<TaskOutput>;
  
  // Cortex
  listPipelines(): Promise<Pipeline[]>;
  getPipeline(name: string): Promise<Pipeline>;
  estimateCost(request: PlanningRequest): Promise<CostEstimate>;
  createSession(request: PlanningRequest): Promise<PlanningSession>;
  streamSession(request: PlanningRequest, handlers: SSEHandlers): () => void;
  getSession(id: string): Promise<PlanningSession>;
  getSessionStages(id: string): Promise<Stage[]>;
  getStageOutput(sessionId: string, stageIndex: number): Promise<StageOutput>;
  getDeliverable(id: string): Promise<Deliverable>;
  pauseSession(id: string): Promise<void>;
  resumeSession(id: string): Promise<void>;
  abortSession(id: string): Promise<void>;
  injectContext(id: string, stageIndex: number, context: string): Promise<void>;
}
```

---

## Summary

This supplemental specification addresses all gaps:

| Gap | Section | Status |
|-----|---------|--------|
| Rate limits for Cortex | §1 | ✅ Complete |
| SSE reconnection | §2 | ✅ Complete |
| Worker management | §3 | ✅ Complete |
| License enforcement | §4 | ✅ Complete |
| NeuroForge routing | §5 | ✅ Complete |
| DataForge schemas | §6 | ✅ Complete |
| Multi-tenant isolation | §7 | ✅ Complete |
| API reconciliation | §8 | ✅ Complete |

**Document Version:** 1.0  
**Last Updated:** December 6, 2025
