/**
 * NeuroForge Overview Dashboard Types
 * Types for the operator dashboard sections
 */

import type { Domain, ModelProvider, InferenceStatus } from "./index";

// ============================================================================
// System Health Metrics
// ============================================================================

export interface SystemHealthMetric {
  id: string;
  label: string;
  value: number | string;
  unit?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: number;
  icon?: string;
  status: "healthy" | "warning" | "critical";
  timestamp: string;
}

export interface SystemHealthSummary {
  metrics: SystemHealthMetric[];
  overallHealth: "healthy" | "degraded" | "unhealthy";
  lastUpdated: string;
}

// ============================================================================
// Pipeline Summary
// ============================================================================

export interface PipelineSummary {
  id: string;
  domain: Domain;
  status: "active" | "inactive" | "paused";
  activeModels: number;
  totalModels: number;
  requestsLast24h: number;
  averageLatencyMs: number;
  successRate: number; // 0.0 to 1.0
  errorCount: number;
  lastRequest?: string;
}

// ============================================================================
// Model Status
// ============================================================================

export interface ModelStatus {
  id: string;
  name: string;
  provider: ModelProvider;
  domain: Domain;
  status: "healthy" | "degraded" | "unhealthy" | "offline";
  latencyMs: number;
  throughput: number; // requests per minute
  errorRate: number; // 0.0 to 1.0
  costPerInference: number;
  successfulRequests: number;
  failedRequests: number;
  isChampion: boolean;
  lastHealthCheck: string;
  availability: number; // 0.0 to 1.0
}

// ============================================================================
// Activity & Logs
// ============================================================================

export interface ActivityEntry {
  id: string;
  timestamp: string;
  type: "inference" | "evaluation" | "error" | "system";
  domain: Domain;
  status: InferenceStatus | "error";
  modelId: string;
  latencyMs: number;
  tokensUsed?: number;
  evaluationScore?: number;
  message: string;
  correlationId?: string;
}

// ============================================================================
// Domain Adapter
// ============================================================================

export interface DomainAdapter {
  domain: Domain;
  isActive: boolean;
  modelsRunning: number;
  requestsProcessed: number;
  averageQuality: number; // 0.0 to 1.0
  evaluationMetrics: {
    coherence: number;
    relevance: number;
    factuality: number;
  };
  lastProcessed: string;
}

// ============================================================================
// Evaluation Highlights
// ============================================================================

export interface EvaluationHighlight {
  modelId: string;
  modelName: string;
  evaluationScore: number; // 0.0 to 1.0
  coherenceScore: number;
  relevanceScore: number;
  factualityScore: number;
  improvement: number; // percentage change from previous
  trend: "up" | "down" | "stable";
  domain: Domain;
}

export interface EvaluationSummary {
  topModels: EvaluationHighlight[];
  averageQuality: number;
  totalEvaluations: number;
  improvementRate: number;
}

// ============================================================================
// Quick Action
// ============================================================================

export interface QuickAction {
  id: string;
  label: string;
  href: string;
  icon?: string;
  description?: string;
  color?: "primary" | "secondary" | "success" | "warning" | "danger";
}

// ============================================================================
// Complete Overview Data
// ============================================================================

export interface OverviewData {
  systemHealth: SystemHealthSummary;
  pipelines: PipelineSummary[];
  models: ModelStatus[];
  activity: ActivityEntry[];
  domains: DomainAdapter[];
  evaluationHighlights: EvaluationSummary;
  quickActions: QuickAction[];
  timestamp: string;
}
