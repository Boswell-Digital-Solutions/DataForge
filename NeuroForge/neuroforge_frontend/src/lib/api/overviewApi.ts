/**
 * Overview API Helper
 * Fetches data for the operator dashboard sections
 */

import { neuroforgeApi } from "./neuroforge";
import type { ApiResponse } from "../types";
import type {
  OverviewData,
  SystemHealthSummary,
  PipelineSummary,
  ModelStatus,
  ActivityEntry,
  DomainAdapter,
  EvaluationSummary,
  QuickAction,
} from "../types/overview";
import { Domain, ModelProvider, InferenceStatus } from "../types";

// ============================================================================
// Mock Data Generators (for development)
// ============================================================================

function generateMockSystemHealth(): SystemHealthSummary {
  return {
    metrics: [
      {
        id: "active-inferences",
        label: "Active Inferences",
        value: 47,
        unit: "requests",
        trend: "up",
        trendValue: 12,
        icon: "⚡",
        status: "healthy",
      },
      {
        id: "avg-latency",
        label: "Avg Latency",
        value: 95,
        unit: "ms",
        trend: "down",
        trendValue: -5,
        icon: "🚀",
        status: "healthy",
      },
      {
        id: "success-rate",
        label: "Success Rate",
        value: "98.7",
        unit: "%",
        trend: "up",
        trendValue: 1.2,
        icon: "✅",
        status: "healthy",
      },
      {
        id: "models-healthy",
        label: "Models Healthy",
        value: "9/10",
        unit: "models",
        trend: "neutral",
        icon: "🧠",
        status: "warning",
      },
    ],
    overallHealth: "healthy",
    lastUpdated: new Date().toISOString(),
  };
}

function generateMockPipelines(): PipelineSummary[] {
  return [
    {
      id: "pipeline-literary",
      domain: Domain.LITERARY,
      status: "active",
      activeModels: 3,
      totalModels: 4,
      requestsLast24h: 1243,
      averageLatencyMs: 87,
      successRate: 0.987,
      errorCount: 16,
      lastRequest: new Date(Date.now() - 2000).toISOString(),
    },
    {
      id: "pipeline-market",
      domain: Domain.MARKET,
      status: "active",
      activeModels: 4,
      totalModels: 5,
      requestsLast24h: 2156,
      averageLatencyMs: 102,
      successRate: 0.994,
      errorCount: 12,
      lastRequest: new Date(Date.now() - 5000).toISOString(),
    },
    {
      id: "pipeline-general",
      domain: Domain.GENERAL,
      status: "active",
      activeModels: 2,
      totalModels: 3,
      requestsLast24h: 876,
      averageLatencyMs: 98,
      successRate: 0.979,
      errorCount: 18,
      lastRequest: new Date(Date.now() - 3000).toISOString(),
    },
  ];
}

function generateMockModels(): ModelStatus[] {
  return [
    {
      id: "model-neural-illm",
      name: "Neural-ILM",
      provider: ModelProvider.OLLAMA,
      domain: Domain.LITERARY,
      status: "healthy",
      latencyMs: 78,
      throughput: 45,
      errorRate: 0.005,
      costPerInference: 0.0,
      successfulRequests: 4521,
      failedRequests: 23,
      isChampion: true,
      lastHealthCheck: new Date(Date.now() - 10000).toISOString(),
      availability: 0.998,
    },
    {
      id: "model-neural-market",
      name: "Neural-Market",
      provider: ModelProvider.OLLAMA,
      domain: Domain.MARKET,
      status: "healthy",
      latencyMs: 92,
      throughput: 38,
      errorRate: 0.008,
      costPerInference: 0.0,
      successfulRequests: 5234,
      failedRequests: 43,
      isChampion: true,
      lastHealthCheck: new Date(Date.now() - 12000).toISOString(),
      availability: 0.993,
    },
    {
      id: "model-gpt4",
      name: "GPT-4",
      provider: ModelProvider.OPENAI,
      domain: Domain.GENERAL,
      status: "degraded",
      latencyMs: 445,
      throughput: 12,
      errorRate: 0.032,
      costPerInference: 0.015,
      successfulRequests: 567,
      failedRequests: 19,
      isChampion: false,
      lastHealthCheck: new Date(Date.now() - 8000).toISOString(),
      availability: 0.945,
    },
    {
      id: "model-claude",
      name: "Claude 3.5",
      provider: ModelProvider.ANTHROPIC,
      domain: Domain.GENERAL,
      status: "healthy",
      latencyMs: 234,
      throughput: 25,
      errorRate: 0.012,
      costPerInference: 0.018,
      successfulRequests: 892,
      failedRequests: 11,
      isChampion: false,
      lastHealthCheck: new Date(Date.now() - 9000).toISOString(),
      availability: 0.987,
    },
  ];
}

function generateMockActivity(): ActivityEntry[] {
  return [
    {
      id: "activity-1",
      type: "inference",
      domain: Domain.LITERARY,
      status: InferenceStatus.COMPLETED,
      modelId: "model-neural-illm",
      latencyMs: 76,
      tokensUsed: 287,
      evaluationScore: 0.92,
      message: "Literary analysis completed",
      correlationId: "corr-001",
    },
    {
      id: "activity-2",
      type: "inference",
      domain: Domain.MARKET,
      status: InferenceStatus.COMPLETED,
      modelId: "model-neural-market",
      latencyMs: 103,
      tokensUsed: 512,
      evaluationScore: 0.87,
      message: "Market trend analysis completed",
      correlationId: "corr-002",
    },
    {
      id: "activity-3",
      type: "inference",
      domain: Domain.GENERAL,
      status: InferenceStatus.COMPLETED,
      modelId: "model-claude",
      latencyMs: 234,
      tokensUsed: 421,
      evaluationScore: 0.89,
      message: "General query processed",
      correlationId: "corr-003",
    },
    {
      id: "activity-4",
      type: "error",
      domain: Domain.MARKET,
      status: "error",
      modelId: "model-gpt4",
      latencyMs: 0,
      message: "Rate limit exceeded",
      correlationId: "corr-004",
    },
    {
      id: "activity-5",
      type: "evaluation",
      domain: Domain.LITERARY,
      status: InferenceStatus.COMPLETED,
      modelId: "model-neural-illm",
      latencyMs: 0,
      message: "Champion model evaluation updated",
      correlationId: "corr-005",
    },
  ];
}

function generateMockDomains(): DomainAdapter[] {
  return [
    {
      domain: Domain.LITERARY,
      isActive: true,
      modelsRunning: 3,
      requestsProcessed: 1243,
      averageQuality: 0.91,
      evaluationMetrics: {
        coherence: 0.94,
        relevance: 0.89,
        factuality: 0.9,
      },
      lastProcessed: new Date(Date.now() - 2000).toISOString(),
    },
    {
      domain: Domain.MARKET,
      isActive: true,
      modelsRunning: 4,
      requestsProcessed: 2156,
      averageQuality: 0.88,
      evaluationMetrics: {
        coherence: 0.91,
        relevance: 0.85,
        factuality: 0.88,
      },
      lastProcessed: new Date(Date.now() - 5000).toISOString(),
    },
    {
      domain: Domain.GENERAL,
      isActive: true,
      modelsRunning: 2,
      requestsProcessed: 876,
      averageQuality: 0.87,
      evaluationMetrics: {
        coherence: 0.89,
        relevance: 0.84,
        factuality: 0.88,
      },
      lastProcessed: new Date(Date.now() - 3000).toISOString(),
    },
  ];
}

function generateMockEvaluationHighlights(): EvaluationSummary {
  return {
    topModels: [
      {
        modelId: "model-neural-illm",
        modelName: "Neural-ILM",
        evaluationScore: 0.936,
        coherenceScore: 0.94,
        relevanceScore: 0.93,
        factualityScore: 0.93,
        improvement: 2.3,
        trend: "up",
        domain: Domain.LITERARY,
      },
      {
        modelId: "model-neural-market",
        modelName: "Neural-Market",
        evaluationScore: 0.912,
        coherenceScore: 0.91,
        relevanceScore: 0.88,
        factualityScore: 0.93,
        improvement: 1.1,
        trend: "stable",
        domain: Domain.MARKET,
      },
      {
        modelId: "model-claude",
        modelName: "Claude 3.5",
        evaluationScore: 0.901,
        coherenceScore: 0.89,
        relevanceScore: 0.92,
        factualityScore: 0.9,
        improvement: -0.5,
        trend: "down",
        domain: Domain.GENERAL,
      },
    ],
    averageQuality: 0.883,
    totalEvaluations: 4275,
    improvementRate: 1.3,
  };
}

function generateMockQuickActions(): QuickAction[] {
  return [
    {
      id: "action-pipelines",
      label: "Configure Pipelines",
      href: "/pipelines",
      icon: "⚙️",
      description: "Manage domain pipelines",
      color: "primary",
    },
    {
      id: "action-playground",
      label: "Open Playground",
      href: "/playground",
      icon: "🎮",
      description: "Test models directly",
      color: "secondary",
    },
    {
      id: "action-evaluations",
      label: "View Evaluations",
      href: "/evaluations",
      icon: "📊",
      description: "Review model performance",
      color: "success",
    },
    {
      id: "action-logs",
      label: "Check Logs",
      href: "/logs",
      icon: "📋",
      description: "Inspect pipeline logs",
      color: "warning",
    },
  ];
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch system health metrics
 */
export async function fetchSystemHealth(): Promise<
  ApiResponse<SystemHealthSummary>
> {
  try {
    // TODO: Replace with actual backend endpoint
    // const response = await neuroforgeApi.client.get('/admin/health');
    // return response.data;

    // Mock for now
    return {
      success: true,
      data: generateMockSystemHealth(),
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: "FETCH_ERROR",
        message:
          error instanceof Error
            ? error.message
            : "Failed to fetch system health",
      },
    };
  }
}

/**
 * Fetch active pipelines summary
 */
export async function fetchPipelinesSummary(): Promise<
  ApiResponse<PipelineSummary[]>
> {
  try {
    // TODO: Replace with actual backend endpoint
    // const response = await neuroforgeApi.fetchPipelines();
    // return response;

    // Mock for now
    return {
      success: true,
      data: generateMockPipelines(),
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: "FETCH_ERROR",
        message:
          error instanceof Error ? error.message : "Failed to fetch pipelines",
      },
    };
  }
}

/**
 * Fetch model status information
 */
export async function fetchModelStatus(): Promise<ApiResponse<ModelStatus[]>> {
  try {
    // TODO: Replace with actual backend endpoint
    // const response = await neuroforgeApi.fetchModels();
    // return response;

    // Mock for now
    return {
      success: true,
      data: generateMockModels(),
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: "FETCH_ERROR",
        message:
          error instanceof Error
            ? error.message
            : "Failed to fetch model status",
      },
    };
  }
}

/**
 * Fetch recent activity entries
 */
export async function fetchRecentActivity(): Promise<
  ApiResponse<ActivityEntry[]>
> {
  try {
    // TODO: Replace with actual backend endpoint
    // const response = await neuroforgeApi.fetchLogs();
    // return response;

    // Mock for now
    return {
      success: true,
      data: generateMockActivity(),
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: "FETCH_ERROR",
        message:
          error instanceof Error
            ? error.message
            : "Failed to fetch recent activity",
      },
    };
  }
}

/**
 * Fetch domain adapter summaries
 */
export async function fetchDomainSummaries(): Promise<
  ApiResponse<DomainAdapter[]>
> {
  try {
    // TODO: Replace with actual backend endpoint
    // const response = await neuroforgeApi.fetchDomainStatus();
    // return response;

    // Mock for now
    return {
      success: true,
      data: generateMockDomains(),
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: "FETCH_ERROR",
        message:
          error instanceof Error
            ? error.message
            : "Failed to fetch domain summaries",
      },
    };
  }
}

/**
 * Fetch evaluation highlights and top models
 */
export async function fetchEvaluationHighlights(): Promise<
  ApiResponse<EvaluationSummary>
> {
  try {
    // TODO: Replace with actual backend endpoint
    // const response = await neuroforgeApi.fetchEvaluations();
    // return response;

    // Mock for now
    return {
      success: true,
      data: generateMockEvaluationHighlights(),
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: "FETCH_ERROR",
        message:
          error instanceof Error
            ? error.message
            : "Failed to fetch evaluation highlights",
      },
    };
  }
}

/**
 * Fetch quick action buttons
 */
export function getQuickActions(): QuickAction[] {
  return generateMockQuickActions();
}

/**
 * Fetch complete overview data
 */
export async function fetchCompleteOverview(): Promise<
  ApiResponse<OverviewData>
> {
  try {
    const [health, pipelines, models, activity, domains, evaluations] =
      await Promise.all([
        fetchSystemHealth(),
        fetchPipelinesSummary(),
        fetchModelStatus(),
        fetchRecentActivity(),
        fetchDomainSummaries(),
        fetchEvaluationHighlights(),
      ]);

    const hasErrors = [
      health,
      pipelines,
      models,
      activity,
      domains,
      evaluations,
    ].some((r) => !r.success);

    if (hasErrors) {
      return {
        success: false,
        error: {
          code: "PARTIAL_FETCH_ERROR",
          message: "Some overview sections failed to load",
        },
      };
    }

    return {
      success: true,
      data: {
        systemHealth: health.data!,
        pipelines: pipelines.data!,
        models: models.data!,
        activity: activity.data!,
        domains: domains.data!,
        evaluationHighlights: evaluations.data!,
        quickActions: getQuickActions(),
        timestamp: new Date().toISOString(),
      },
    };
  } catch (error) {
    return {
      success: false,
      error: {
        code: "FETCH_ERROR",
        message:
          error instanceof Error
            ? error.message
            : "Failed to fetch overview data",
      },
    };
  }
}
