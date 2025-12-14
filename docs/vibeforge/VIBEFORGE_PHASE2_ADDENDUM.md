# VibeForge Phase 2: Supplemental Addendum

**Date:** December 6, 2025  
**Status:** Refinements to VIBEFORGE_PHASE2_SUPPLEMENTAL_SPEC.md

---

## §A: Orchestrator Queue Strategy

The Cortex task queue uses **license-tier priority with FIFO within tier**:

```
Priority 1 (highest): Enterprise sessions
Priority 2: Pro sessions  
Priority 3: Trial sessions
Priority 4 (lowest): Free sessions (if ever enabled)
```

Within each priority tier, sessions execute in FIFO order. This ensures paying customers get predictable latency while free-tier users (future feature) don't starve—they simply wait longer during peak load. Stage execution within a session is strictly sequential (no stage-level priority).

---

## §B: Session Concurrency Limits

Add to license tier configuration:

| Tier | Concurrent Planning Sessions | Concurrent Agents | SSE Connections |
|------|------------------------------|-------------------|-----------------|
| Free | 0 (feature disabled) | 1 | 2 |
| Trial | 2 | 5 | 5 |
| Pro | 5 | 20 | 15 |
| Enterprise | unlimited | unlimited | unlimited |

**Enforcement:**

```python
# In LicenseEnforcer.check_concurrency()
async def check_session_concurrency(self, user_id: str, tier: LicenseTier) -> bool:
    """Check if user can start a new planning session."""
    limits = {
        LicenseTier.FREE: 0,
        LicenseTier.TRIAL: 2,
        LicenseTier.PRO: 5,
        LicenseTier.ENTERPRISE: float('inf'),
    }
    
    current = await self.redis.scard(f"sessions:active:{user_id}")
    return current < limits[tier]
```

**Redis tracking:**

```
sessions:active:{user_id}  →  SET of active session IDs
```

On session start: `SADD sessions:active:{user_id} {session_id}`  
On session end: `SREM sessions:active:{user_id} {session_id}`

---

## §C: SSE Reconnection Protocol (Backend)

Add to ForgeAgents streaming endpoint:

### Server-Side Requirements

```python
@dataclass
class SessionStreamState:
    session_id: str
    last_event_id: int
    stage_index: int
    stage_token_offset: int  # Characters already sent in current stage
    created_at: datetime
    ttl: int = 300  # 5 minutes

# Redis key
stream_state:{session_id}  →  JSON(SessionStreamState)
```

### Reconnection Flow

1. **Client disconnects** (network drop, Tauri app backgrounded)

2. **Client reconnects** with headers:
   ```
   Last-Event-ID: {last_received_event_id}
   X-Session-ID: {session_id}
   ```

3. **Server checks state:**
   ```python
   @router.get("/sessions/{session_id}/stream/resume")
   async def resume_stream(
       session_id: str,
       last_event_id: int = Header(None, alias="Last-Event-ID"),
   ):
       state = await redis.get(f"stream_state:{session_id}")
       if not state:
           raise HTTPException(410, "Session stream expired")
       
       # Resume from last known position
       return StreamingResponse(
           resume_session_stream(session_id, state, last_event_id),
           media_type="text/event-stream",
       )
   ```

4. **Server replays missed events:**
   - Events are buffered in Redis list: `stream_events:{session_id}` (last 100)
   - On reconnect, replay events with `id > last_event_id`
   - If stage was mid-stream, send `stage_resumed` event with `token_offset`

### Event ID Format

```
{session_id}-{stage_index}-{sequence}

Example: session-abc123-2-47
         └── session ──┘ │  └── 47th event in stage 2
                        └── stage index
```

### Client Behavior (Tauri/VibeForge)

```typescript
class SSEManager {
  private lastEventId: string | null = null;
  
  async reconnect(): Promise<void> {
    const headers: Record<string, string> = {
      'Accept': 'text/event-stream',
    };
    
    if (this.lastEventId) {
      headers['Last-Event-ID'] = this.lastEventId;
    }
    
    // Use resume endpoint if we have state
    const endpoint = this.lastEventId 
      ? `/sessions/${this.sessionId}/stream/resume`
      : `/sessions/${this.sessionId}/stream`;
    
    // Exponential backoff handled by existing SSEManager
  }
  
  handleEvent(event: SSEEvent): void {
    if (event.id) {
      this.lastEventId = event.id;
    }
    // ... process event
  }
}
```

---

## §D: Worker Manager Specification

### Worker Pool Configuration

```python
@dataclass
class WorkerManagerConfig:
    min_workers: int = 2
    max_workers: int = 10
    worker_max_lifetime: int = 3600      # 1 hour, then recycle
    worker_max_tasks: int = 100          # Max tasks before recycle
    health_check_interval: int = 30      # Seconds
    task_timeout: int = 600              # 10 minutes per stage
    crash_restart_delay: int = 5         # Seconds before restart
    crash_backoff_max: int = 60          # Max restart delay after repeated crashes
```

### Supervision Strategy

**Restart policy:** Workers are supervised with exponential backoff restart:

```python
class WorkerSupervisor:
    """Supervises worker processes with restart-on-crash."""
    
    async def supervise(self, worker_id: str):
        restart_count = 0
        
        while True:
            try:
                await self.run_worker(worker_id)
                restart_count = 0  # Reset on clean exit
                
            except WorkerCrashError as e:
                restart_count += 1
                delay = min(
                    self.config.crash_restart_delay * (2 ** restart_count),
                    self.config.crash_backoff_max
                )
                
                logger.error(f"Worker {worker_id} crashed ({restart_count}x), "
                            f"restarting in {delay}s: {e}")
                
                await asyncio.sleep(delay)
                
                # Alert if repeated crashes
                if restart_count >= 3:
                    await self.alert_ops(f"Worker {worker_id} unstable")
```

### Crash Behavior

| Scenario | Behavior |
|----------|----------|
| Worker crashes mid-task | Task marked FAILED, returned to queue with `attempts += 1` |
| Worker hangs (no heartbeat for 60s) | Supervisor kills process, restarts |
| Worker exceeds max_lifetime | Graceful shutdown after current task |
| Worker exceeds max_tasks | Graceful shutdown after current task |
| All workers crash | Alert ops, continue restart attempts |

### Health Monitoring

```python
# Worker heartbeat
worker:heartbeat:{worker_id}  →  timestamp (TTL: 60s)

# Worker metrics
worker:metrics:{worker_id}  →  {
    "tasks_completed": int,
    "tasks_failed": int,
    "uptime_seconds": int,
    "memory_mb": int,
    "last_task_duration_ms": int
}
```

### Auto-Scaling Rules

```python
async def should_scale_up(self) -> bool:
    """Scale up if queue depth > 5 and below max workers."""
    queue_depth = await self.get_queue_depth()
    current_workers = len(self.active_workers)
    return queue_depth > 5 and current_workers < self.config.max_workers

async def should_scale_down(self) -> bool:
    """Scale down if workers idle > 5 min and above min workers."""
    idle_workers = [w for w in self.active_workers if w.idle_seconds > 300]
    return len(idle_workers) > 0 and len(self.active_workers) > self.config.min_workers
```

---

## Summary of Changes

| Section | Addition |
|---------|----------|
| §A | Queue uses license-tier priority + FIFO within tier |
| §B | Session concurrency limits: Free=0, Trial=2, Pro=5, Enterprise=∞ |
| §C | SSE reconnection with Last-Event-ID, server-side state, event replay |
| §D | Worker pool: 2-10 workers, supervised restart, health checks, auto-scale |

These refinements complete the operational spec for production deployment.
