/**
 * NeuroForge Frontend TypeScript Types
 * Defines all domain models and API contracts
 */

// ============================================================================
// Enums & Constants
// ============================================================================

export enum Domain {
  LITERARY = "literary",
  MARKET = "market",
  GENERAL = "general",
}

export enum TaskType {
  ANALYSIS = "analysis",
  GENERATION = "generation",
  CLASSIFICATION = "classification",
  EXTRACTION = "extraction",
}

export enum ModelProvider {
  OLLAMA = "ollama",
  ANTHROPIC = "anthropic",
  OPENAI = "openai",
}

export enum RoutingStrategy {
  DOMAIN_OPTIMIZED = "domain_optimized",
  COST_OPTIMIZED = "cost_optimized",
  SPEED_OPTIMIZED = "speed_optimized",
  QUALITY_OPTIMIZED = "quality_optimized",
}

export enum InferenceStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
}

// ============================================================================
// Pipeline & Configuration
// ============================================================================

export interface DomainConfig {
  id: string;
  name: Domain;
  label: string;
  description: string;
  promptTemplates: PromptTemplate[];
  policyTokens: string[];
  contextScopes: string[];
  evaluationRubric: EvaluationDimension[];
}

export interface PromptTemplate {
  id: string;
  name: string;
  template: string;
  variables: string[];
  category: "system" | "user" | "context";
}

export interface PipelineConfig {
  id: string;
  name: string;
  domain: Domain;
  description: string;
  adapterName: string;
  routingStrategy: RoutingStrategy;
  models: ModelReference[];
  contextTTL: number;
  maxTokens: number;
  createdAt: string;
  updatedAt: string;
}

export interface ModelReference {
  modelId: string;
  provider: ModelProvider;
  priority: number;
  enabled: boolean;
}

// ============================================================================
// Models & Routing
// ============================================================================

export interface ModelCatalog {
  id: string;
  name: string;
  provider: ModelProvider;
  capability: string; // e.g., 'literary-analysis', 'market-research'
  cost: ModelCost;
  health: ModelHealth;
  lastUsed: string;
  isChampion: boolean;
}

export interface ModelCost {
  inputCostPerK: number;
  outputCostPerK: number;
  estimatedCostPerInference: number;
  currency: "USD" | "EUR";
}

export interface ModelHealth {
  status: "healthy" | "degraded" | "unhealthy";
  latencyMs: number;
  errorRate: number;
  availabilityPercent: number;
  lastHealthCheck: string;
}

export interface RoutingRule {
  id: string;
  condition: string; // e.g., "domain == 'literary' && task_type == 'analysis'"
  targetModel: string;
  fallbackModel?: string;
  priority: number;
}

// ============================================================================
// Inference & Evaluation
// ============================================================================

export interface InferenceRequest {
  domain: Domain;
  taskType: TaskType;
  contextPackId: string;
  userQuery: string;
  additionalContext?: string;
  maxTokens?: number;
  modelOverride?: string;
}

export interface InferenceResult {
  inferenceId: string;
  status: InferenceStatus;
  output: string;
  modelId: string;
  model_id?: string; // alias for compatibility
  latencyMs: number;
  latency_ms?: number; // alias for compatibility
  tokensUsed: number;
  evaluation: EvaluationResult;
  evaluation_score?: number; // convenience property (0.0-1.0)
  metadata: Record<string, unknown>;
  correlationId?: string;
  createdAt: string;
}

export interface EvaluationResult {
  passed: boolean;
  scores: EvaluationScore[];
  recommendations: string[];
  reasoning: string;
}

export interface EvaluationScore {
  metric: string;
  score: number; // 0.0 to 1.0
  weight: number;
  reasoning?: string;
}

export interface EvaluationDimension {
  name: string;
  weight: number;
  description: string;
  rubric: string[];
}

export interface EvaluationRun {
  id: string;
  domain: Domain;
  pipelineId: string;
  modelsTested: string[];
  batchSize: number;
  results: InferenceResult[];
  summary: RunSummary;
  createdAt: string;
}

export interface RunSummary {
  averageQualityScore: number;
  averageLatencyMs: number;
  totalCost: number;
  successRate: number;
  recommendedChampion: string;
}

// ============================================================================
// Logs & Provenance
// ============================================================================

export interface LogEntry {
  id: string;
  timestamp: string;
  created_at: string;
  level: "DEBUG" | "INFO" | "WARN" | "ERROR";
  service: string;
  message: string;
  correlationId?: string;
  metadata?: Record<string, unknown>;
  domain?: string;
  task_type?: string;
  model_id?: string;
  evaluation_score?: number;
  latency_ms?: number;
}

export interface ProvenanceRecord {
  inferenceId: string;
  dataforgeProvenanceId: string;
  context: Record<string, unknown>;
  prompt: string;
  response: string;
  evaluation: EvaluationResult;
  timestamp: string;
}

// ============================================================================
// API Response Wrappers
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  meta?: {
    requestId: string;
    timestamp: string;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// Dashboard & Analytics
// ============================================================================

export interface DashboardStats {
  activeDomains: number;
  runningModels: number;
  recentRuns: number;
  averageLatencyMs: number;
  errorRate: number;
  totalCost: number;
}

export interface ModelPerformanceMetric {
  modelId: string;
  domain: Domain;
  qualityScore: number;
  latencyMs: number;
  cost: number;
  successRate: number;
  lastEvaluated: string;
}

export interface ChampionModel {
  modelId: string;
  domain: Domain;
  score: number;
  promotedAt: string;
  reignDuration: number;
  reasonForSelection: string;
}
