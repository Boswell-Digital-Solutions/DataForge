/**
 * NeuroForge API Service
 * Centralized HTTP client for FastAPI backend communication
 */

import axios from "axios";
import type { AxiosInstance } from "axios";
import type {
  ApiResponse,
  DomainConfig,
  PipelineConfig,
  ModelCatalog,
  InferenceRequest,
  InferenceResult,
  EvaluationRun,
  LogEntry,
  DashboardStats,
  ChampionModel,
} from "../types";

class NeuroForgeClient {
  private client: AxiosInstance;
  private baseURL: string;

  constructor(baseURL: string = "http://localhost:8000/api/v1") {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": "dev-key", // Development API key
      },
      timeout: 30000,
    });

    // Add request interceptor for correlation IDs
    this.client.interceptors.request.use((config) => {
      const correlationId = crypto.randomUUID();
      config.headers["X-Request-ID"] = correlationId;
      return config;
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error("API Error:", error.response?.data || error.message);
        throw error;
      }
    );
  }

  // ========================================================================
  // Health & Status
  // ========================================================================

  async getHealth(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>("/health");
    return response.data;
  }

  async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
    const response = await this.client.get<ApiResponse<DashboardStats>>(
      "/admin/dashboard"
    );
    return response.data;
  }

  // ========================================================================
  // Pipelines
  // ========================================================================

  async fetchPipelines(): Promise<ApiResponse<PipelineConfig[]>> {
    const response = await this.client.get<ApiResponse<PipelineConfig[]>>(
      "/pipelines"
    );
    return response.data;
  }

  async fetchPipeline(id: string): Promise<ApiResponse<PipelineConfig>> {
    const response = await this.client.get<ApiResponse<PipelineConfig>>(
      `/pipelines/${id}`
    );
    return response.data;
  }

  async createPipeline(
    pipeline: Partial<PipelineConfig>
  ): Promise<ApiResponse<PipelineConfig>> {
    const response = await this.client.post<ApiResponse<PipelineConfig>>(
      "/pipelines",
      pipeline
    );
    return response.data;
  }

  async updatePipeline(
    id: string,
    updates: Partial<PipelineConfig>
  ): Promise<ApiResponse<PipelineConfig>> {
    const response = await this.client.put<ApiResponse<PipelineConfig>>(
      `/pipelines/${id}`,
      updates
    );
    return response.data;
  }

  async deletePipeline(id: string): Promise<ApiResponse<void>> {
    const response = await this.client.delete<ApiResponse<void>>(
      `/pipelines/${id}`
    );
    return response.data;
  }

  // ========================================================================
  // Domains & Adapters
  // ========================================================================

  async fetchDomains(): Promise<ApiResponse<DomainConfig[]>> {
    const response = await this.client.get<ApiResponse<DomainConfig[]>>(
      "/domains"
    );
    return response.data;
  }

  async fetchDomain(domainName: string): Promise<ApiResponse<DomainConfig>> {
    const response = await this.client.get<ApiResponse<DomainConfig>>(
      `/domains/${domainName}`
    );
    return response.data;
  }

  async updateDomain(
    domainName: string,
    updates: Partial<DomainConfig>
  ): Promise<ApiResponse<DomainConfig>> {
    const response = await this.client.put<ApiResponse<DomainConfig>>(
      `/domains/${domainName}`,
      updates
    );
    return response.data;
  }

  // ========================================================================
  // Models & Routing
  // ========================================================================

  async fetchModels(): Promise<ApiResponse<ModelCatalog[]>> {
    const response = await this.client.get<ApiResponse<ModelCatalog[]>>(
      "/models"
    );
    return response.data;
  }

  async fetchModel(id: string): Promise<ApiResponse<ModelCatalog>> {
    const response = await this.client.get<ApiResponse<ModelCatalog>>(
      `/models/${id}`
    );
    return response.data;
  }

  async getChampionModels(): Promise<ApiResponse<ChampionModel[]>> {
    const response = await this.client.get<ApiResponse<ChampionModel[]>>(
      "/models/champions"
    );
    return response.data;
  }

  // ========================================================================
  // Inference & Playground
  // ========================================================================

  async runInference(
    request: InferenceRequest
  ): Promise<ApiResponse<InferenceResult>> {
    const response = await this.client.post<ApiResponse<InferenceResult>>(
      "/inference",
      request
    );
    return response.data;
  }

  async getInferenceResult(
    inferenceId: string
  ): Promise<ApiResponse<InferenceResult>> {
    const response = await this.client.get<ApiResponse<InferenceResult>>(
      `/inference/${inferenceId}`
    );
    return response.data;
  }

  async getInferenceHistory(
    domain?: string,
    limit: number = 50
  ): Promise<ApiResponse<InferenceResult[]>> {
    const params = new URLSearchParams();
    if (domain) params.append("domain", domain);
    params.append("limit", limit.toString());

    const response = await this.client.get<ApiResponse<InferenceResult[]>>(
      `/inference/history?${params.toString()}`
    );
    return response.data;
  }

  // ========================================================================
  // Evaluations & Experiments
  // ========================================================================

  async fetchEvaluationRuns(
    domain?: string,
    pipelineId?: string
  ): Promise<ApiResponse<EvaluationRun[]>> {
    const params = new URLSearchParams();
    if (domain) params.append("domain", domain);
    if (pipelineId) params.append("pipeline_id", pipelineId);

    const response = await this.client.get<ApiResponse<EvaluationRun[]>>(
      `/evaluations?${params.toString()}`
    );
    return response.data;
  }

  async fetchEvaluationRun(id: string): Promise<ApiResponse<EvaluationRun>> {
    const response = await this.client.get<ApiResponse<EvaluationRun>>(
      `/evaluations/${id}`
    );
    return response.data;
  }

  async createEvaluationRun(
    pipelineId: string,
    batchSize: number = 10
  ): Promise<ApiResponse<EvaluationRun>> {
    const response = await this.client.post<ApiResponse<EvaluationRun>>(
      "/evaluations",
      {
        pipeline_id: pipelineId,
        batch_size: batchSize,
      }
    );
    return response.data;
  }

  // ========================================================================
  // Logs & Audit Trail
  // ========================================================================

  async fetchLogs(
    domain?: string,
    level?: string,
    limit: number = 100
  ): Promise<ApiResponse<LogEntry[]>> {
    const params = new URLSearchParams();
    if (domain) params.append("domain", domain);
    if (level) params.append("level", level);
    params.append("limit", limit.toString());

    const response = await this.client.get<ApiResponse<LogEntry[]>>(
      `/admin/logs?${params.toString()}`
    );
    return response.data;
  }

  async getAuditTrail(): Promise<ApiResponse<unknown>> {
    const response = await this.client.get<ApiResponse<unknown>>(
      "/admin/audit-trail"
    );
    return response.data;
  }

  // ========================================================================
  // Analytics (Phase 3.0)
  // ========================================================================

  async getPerformanceTrends(
    timeRange: string = "24h"
  ): Promise<ApiResponse<Record<string, unknown>>> {
    const response = await this.client.get<
      ApiResponse<Record<string, unknown>>
    >(`/admin/analytics/performance-over-time?time_range=${timeRange}`);
    return response.data;
  }

  async getComparativeAnalysis(): Promise<
    ApiResponse<Record<string, unknown>>
  > {
    const response = await this.client.get<
      ApiResponse<Record<string, unknown>>
    >("/admin/analytics/comparative-analysis");
    return response.data;
  }

  async getPerformancePredictions(
    horizon: string = "24h"
  ): Promise<ApiResponse<Record<string, unknown>>> {
    const response = await this.client.get<
      ApiResponse<Record<string, unknown>>
    >(`/admin/analytics/predictions?horizon=${horizon}`);
    return response.data;
  }

  async getAnomalies(): Promise<ApiResponse<Record<string, unknown>>> {
    const response = await this.client.get<
      ApiResponse<Record<string, unknown>>
    >("/admin/analytics/anomalies");
    return response.data;
  }
}

// Export singleton instance
export const neuroforgeApi = new NeuroForgeClient();

// Export client class for testing/custom instances
export { NeuroForgeClient };
