// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use sqlx::{sqlite::SqlitePool, Row};
use std::env;

// ===========================================================================
// Data Models
// ===========================================================================

#[derive(Debug, Serialize, Deserialize)]
struct SystemHealth {
    dataforge_status: String,
    dataforge_uptime: f64,
    neuroforge_status: String,
    neuroforge_uptime: f64,
    rake_status: String,
    rake_uptime: f64,
    forgeagents_status: String,
    forgeagents_uptime: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct RecentEvent {
    event_id: String,
    timestamp: String,
    service: String,
    event_type: String,
    severity: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct DataForgeMetrics {
    total_searches: i64,
    avg_search_duration: f64,
    avg_similarity: f64,
    error_rate: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct NeuroForgeMetrics {
    total_requests: i64,
    total_tokens: i64,
    total_cost: f64,
    avg_evaluation_score: f64,
    top_models: Vec<ModelMetric>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ModelMetric {
    model: String,
    requests: i64,
    tokens: i64,
    cost: f64,
    avg_latency: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct TimeSeriesPoint {
    timestamp: String,
    value: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct CostOverTime {
    datapoints: Vec<TimeSeriesPoint>,
}

#[derive(Debug, Serialize, Deserialize)]
struct TokenUsageOverTime {
    datapoints: Vec<TimeSeriesPoint>,
}

#[derive(Debug, Serialize, Deserialize)]
struct SearchPerformanceOverTime {
    datapoints: Vec<TimeSeriesPoint>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ForgeAgentsMetrics {
    active_agents: i64,
    total_tasks: i64,
    avg_latency_ms: f64,
    success_rate: f64,
    recent_agents: Vec<AgentInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
struct AgentInfo {
    agent_id: String,
    agent_name: String,
    status: String,
    tasks_completed: i64,
    avg_latency_ms: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct AgentActivityOverTime {
    datapoints: Vec<TimeSeriesPoint>,
}

#[derive(Debug, Serialize, Deserialize)]
struct AgentLatencyOverTime {
    datapoints: Vec<TimeSeriesPoint>,
}

#[derive(Debug, Serialize, Deserialize)]
struct RakeMetrics {
    total_pipelines: i64,
    active_pipelines: i64,
    records_ingested: i64,
    ingestion_rate: f64,
    error_rate: f64,
    recent_pipelines: Vec<PipelineInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
struct PipelineInfo {
    pipeline_id: String,
    pipeline_name: String,
    status: String,
    records_processed: i64,
    last_run: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct IngestionOverTime {
    datapoints: Vec<TimeSeriesPoint>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ErrorRateOverTime {
    datapoints: Vec<TimeSeriesPoint>,
}

// ===========================================================================
// Database Connection
// ===========================================================================

async fn get_db_pool() -> Result<SqlitePool, String> {
    // Use DataForge's database for telemetry
    let database_url = env::var("DATABASE_URL")
        .unwrap_or_else(|_| {
            "/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db".to_string()
        });

    let db_url = if database_url.starts_with("sqlite:") {
        database_url
    } else {
        format!("sqlite://{}", database_url)
    };

    SqlitePool::connect(&db_url)
        .await
        .map_err(|e| format!("Failed to connect to database: {}", e))
}

// ===========================================================================
// IPC Commands
// ===========================================================================

#[tauri::command]
async fn get_system_health() -> Result<SystemHealth, String> {
    let pool = get_db_pool().await?;

    // Query for DataForge health (events in last 5 minutes)
    let dataforge_recent = sqlx::query(
        "SELECT COUNT(*) as count FROM events
         WHERE service = 'dataforge'
         AND datetime(timestamp) > datetime('now', '-5 minutes')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?
    .get::<i64, _>("count");

    // Query for NeuroForge health
    let neuroforge_recent = sqlx::query(
        "SELECT COUNT(*) as count FROM events
         WHERE service = 'neuroforge'
         AND datetime(timestamp) > datetime('now', '-5 minutes')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?
    .get::<i64, _>("count");

    // Query for ForgeAgents health
    let forgeagents_recent = sqlx::query(
        "SELECT COUNT(*) as count FROM events
         WHERE service = 'forgeagents'
         AND datetime(timestamp) > datetime('now', '-5 minutes')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?
    .get::<i64, _>("count");

    // Query for Rake health
    let rake_recent = sqlx::query(
        "SELECT COUNT(*) as count FROM events
         WHERE service = 'rake'
         AND datetime(timestamp) > datetime('now', '-5 minutes')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?
    .get::<i64, _>("count");

    // Calculate uptime (% of successful vs total events in last 24h)
    let dataforge_uptime = calculate_uptime(&pool, "dataforge").await?;
    let neuroforge_uptime = calculate_uptime(&pool, "neuroforge").await?;
    let forgeagents_uptime = calculate_uptime(&pool, "forgeagents").await?;
    let rake_uptime = calculate_uptime(&pool, "rake").await?;

    Ok(SystemHealth {
        dataforge_status: if dataforge_recent > 0 { "UP".to_string() } else { "DOWN".to_string() },
        dataforge_uptime,
        neuroforge_status: if neuroforge_recent > 0 { "UP".to_string() } else { "DOWN".to_string() },
        neuroforge_uptime,
        rake_status: if rake_recent > 0 { "UP".to_string() } else { "NOT_DEPLOYED".to_string() },
        rake_uptime,
        forgeagents_status: if forgeagents_recent > 0 { "UP".to_string() } else { "DOWN".to_string() },
        forgeagents_uptime,
    })
}

async fn calculate_uptime(pool: &SqlitePool, service: &str) -> Result<f64, String> {
    let result = sqlx::query(
        "SELECT
            COUNT(*) FILTER (WHERE severity != 'error') as success,
            COUNT(*) as total
         FROM events
         WHERE service = ?
         AND datetime(timestamp) > datetime('now', '-24 hours')"
    )
    .bind(service)
    .fetch_one(pool)
    .await
    .map_err(|e| e.to_string())?;

    let success: i64 = result.get("success");
    let total: i64 = result.get("total");

    if total == 0 {
        Ok(100.0)
    } else {
        Ok((success as f64 / total as f64) * 100.0)
    }
}

#[tauri::command]
async fn get_recent_events(limit: i64) -> Result<Vec<RecentEvent>, String> {
    let pool = get_db_pool().await?;

    let events = sqlx::query_as::<_, (String, String, String, String, String)>(
        "SELECT event_id, timestamp, service, event_type, severity
         FROM events
         ORDER BY timestamp DESC
         LIMIT ?"
    )
    .bind(limit)
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|(event_id, timestamp, service, event_type, severity)| RecentEvent {
        event_id,
        timestamp,
        service,
        event_type,
        severity,
    })
    .collect();

    Ok(events)
}

#[tauri::command]
async fn get_dataforge_metrics() -> Result<DataForgeMetrics, String> {
    let pool = get_db_pool().await?;

    // Get search metrics
    let metrics = sqlx::query(
        "SELECT
            COUNT(*) as total_searches,
            AVG(CAST(json_extract(metrics, '$.duration_ms') AS FLOAT)) as avg_duration,
            AVG(CAST(json_extract(metrics, '$.avg_similarity') AS FLOAT)) as avg_similarity
         FROM events
         WHERE service = 'dataforge' AND event_type = 'query'"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?;

    // Calculate error rate
    let error_rate_result = sqlx::query(
        "SELECT
            CAST(COUNT(*) FILTER (WHERE event_type = 'query_error') AS FLOAT) /
            NULLIF(COUNT(*), 0) * 100.0 as error_rate
         FROM events
         WHERE service = 'dataforge'
         AND event_type IN ('query', 'query_error')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?;

    Ok(DataForgeMetrics {
        total_searches: metrics.get::<Option<i64>, _>("total_searches").unwrap_or(0),
        avg_search_duration: metrics.get::<Option<f64>, _>("avg_duration").unwrap_or(0.0),
        avg_similarity: metrics.get::<Option<f64>, _>("avg_similarity").unwrap_or(0.0),
        error_rate: error_rate_result.get::<Option<f64>, _>("error_rate").unwrap_or(0.0),
    })
}

#[tauri::command]
async fn get_neuroforge_metrics() -> Result<NeuroForgeMetrics, String> {
    let pool = get_db_pool().await?;

    // Get overall metrics
    let overall = sqlx::query(
        "SELECT
            COUNT(*) as total_requests,
            SUM(CAST(json_extract(metrics, '$.tokens_total') AS INTEGER)) as total_tokens,
            SUM(CAST(json_extract(metrics, '$.cost_usd') AS FLOAT)) as total_cost,
            AVG(CAST(json_extract(metrics, '$.evaluation_score') AS FLOAT)) as avg_score
         FROM events
         WHERE service = 'neuroforge' AND event_type = 'model_request'"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?;

    // Get per-model metrics
    let models = sqlx::query(
        "SELECT
            json_extract(metadata, '$.model') as model,
            COUNT(*) as requests,
            SUM(CAST(json_extract(metrics, '$.tokens_total') AS INTEGER)) as tokens,
            SUM(CAST(json_extract(metrics, '$.cost_usd') AS FLOAT)) as cost,
            AVG(CAST(json_extract(metrics, '$.duration_ms') AS FLOAT)) as avg_latency
         FROM events
         WHERE service = 'neuroforge' AND event_type = 'model_request'
         GROUP BY json_extract(metadata, '$.model')
         ORDER BY cost DESC
         LIMIT 5"
    )
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| ModelMetric {
        model: row.get::<Option<String>, _>("model").unwrap_or_else(|| "unknown".to_string()),
        requests: row.get::<Option<i64>, _>("requests").unwrap_or(0),
        tokens: row.get::<Option<i64>, _>("tokens").unwrap_or(0),
        cost: row.get::<Option<f64>, _>("cost").unwrap_or(0.0),
        avg_latency: row.get::<Option<f64>, _>("avg_latency").unwrap_or(0.0),
    })
    .collect();

    Ok(NeuroForgeMetrics {
        total_requests: overall.get::<Option<i64>, _>("total_requests").unwrap_or(0),
        total_tokens: overall.get::<Option<i64>, _>("total_tokens").unwrap_or(0),
        total_cost: overall.get::<Option<f64>, _>("total_cost").unwrap_or(0.0),
        avg_evaluation_score: overall.get::<Option<f64>, _>("avg_score").unwrap_or(0.0),
        top_models: models,
    })
}

#[tauri::command]
async fn get_cost_over_time(hours: i64) -> Result<CostOverTime, String> {
    let pool = get_db_pool().await?;

    let datapoints = sqlx::query(
        "SELECT
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            SUM(CAST(json_extract(metrics, '$.cost_usd') AS FLOAT)) as total_cost
         FROM events
         WHERE service = 'neuroforge'
         AND event_type = 'model_request'
         AND datetime(timestamp) > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    )
    .bind(format!("-{}", hours))
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| TimeSeriesPoint {
        timestamp: row.get::<String, _>("hour"),
        value: row.get::<Option<f64>, _>("total_cost").unwrap_or(0.0),
    })
    .collect();

    Ok(CostOverTime { datapoints })
}

#[tauri::command]
async fn get_token_usage_over_time(hours: i64) -> Result<TokenUsageOverTime, String> {
    let pool = get_db_pool().await?;

    let datapoints = sqlx::query(
        "SELECT
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            SUM(CAST(json_extract(metrics, '$.tokens_total') AS INTEGER)) as total_tokens
         FROM events
         WHERE service = 'neuroforge'
         AND event_type = 'model_request'
         AND datetime(timestamp) > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    )
    .bind(format!("-{}", hours))
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| TimeSeriesPoint {
        timestamp: row.get::<String, _>("hour"),
        value: row.get::<Option<i64>, _>("total_tokens").unwrap_or(0) as f64,
    })
    .collect();

    Ok(TokenUsageOverTime { datapoints })
}

#[tauri::command]
async fn get_search_performance_over_time(hours: i64) -> Result<SearchPerformanceOverTime, String> {
    let pool = get_db_pool().await?;

    let datapoints = sqlx::query(
        "SELECT
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            AVG(CAST(json_extract(metrics, '$.duration_ms') AS FLOAT)) as avg_duration
         FROM events
         WHERE service = 'dataforge'
         AND event_type = 'query'
         AND datetime(timestamp) > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    )
    .bind(format!("-{}", hours))
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| TimeSeriesPoint {
        timestamp: row.get::<String, _>("hour"),
        value: row.get::<Option<f64>, _>("avg_duration").unwrap_or(0.0),
    })
    .collect();

    Ok(SearchPerformanceOverTime { datapoints })
}

#[tauri::command]
async fn get_forgeagents_metrics() -> Result<ForgeAgentsMetrics, String> {
    let pool = get_db_pool().await?;

    // Get overall agent metrics
    let overall = sqlx::query(
        "SELECT
            COUNT(DISTINCT json_extract(metadata, '$.agent_id')) as active_agents,
            COUNT(*) as total_tasks,
            AVG(CAST(json_extract(metrics, '$.duration_ms') AS FLOAT)) as avg_latency,
            CAST(COUNT(*) FILTER (WHERE event_type = 'agent_task_completed') AS FLOAT) /
            NULLIF(COUNT(*), 0) * 100.0 as success_rate
         FROM events
         WHERE service = 'forgeagents'
         AND event_type IN ('agent_task_started', 'agent_task_completed', 'agent_task_failed')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?;

    // Get recent agent activity (top 5 agents)
    let agents = sqlx::query(
        "SELECT
            json_extract(metadata, '$.agent_id') as agent_id,
            json_extract(metadata, '$.agent_name') as agent_name,
            json_extract(metadata, '$.status') as status,
            COUNT(*) as tasks_completed,
            AVG(CAST(json_extract(metrics, '$.duration_ms') AS FLOAT)) as avg_latency
         FROM events
         WHERE service = 'forgeagents'
         AND event_type = 'agent_task_completed'
         GROUP BY agent_id
         ORDER BY tasks_completed DESC
         LIMIT 5"
    )
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| AgentInfo {
        agent_id: row.get::<Option<String>, _>("agent_id").unwrap_or_else(|| "unknown".to_string()),
        agent_name: row.get::<Option<String>, _>("agent_name").unwrap_or_else(|| "Unknown Agent".to_string()),
        status: row.get::<Option<String>, _>("status").unwrap_or_else(|| "active".to_string()),
        tasks_completed: row.get::<Option<i64>, _>("tasks_completed").unwrap_or(0),
        avg_latency_ms: row.get::<Option<f64>, _>("avg_latency").unwrap_or(0.0),
    })
    .collect();

    Ok(ForgeAgentsMetrics {
        active_agents: overall.get::<Option<i64>, _>("active_agents").unwrap_or(0),
        total_tasks: overall.get::<Option<i64>, _>("total_tasks").unwrap_or(0),
        avg_latency_ms: overall.get::<Option<f64>, _>("avg_latency").unwrap_or(0.0),
        success_rate: overall.get::<Option<f64>, _>("success_rate").unwrap_or(0.0),
        recent_agents: agents,
    })
}

#[tauri::command]
async fn get_agent_activity_over_time(hours: i64) -> Result<AgentActivityOverTime, String> {
    let pool = get_db_pool().await?;

    let datapoints = sqlx::query(
        "SELECT
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            COUNT(*) as task_count
         FROM events
         WHERE service = 'forgeagents'
         AND event_type = 'agent_task_completed'
         AND datetime(timestamp) > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    )
    .bind(format!("-{}", hours))
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| TimeSeriesPoint {
        timestamp: row.get::<String, _>("hour"),
        value: row.get::<Option<i64>, _>("task_count").unwrap_or(0) as f64,
    })
    .collect();

    Ok(AgentActivityOverTime { datapoints })
}

#[tauri::command]
async fn get_agent_latency_over_time(hours: i64) -> Result<AgentLatencyOverTime, String> {
    let pool = get_db_pool().await?;

    let datapoints = sqlx::query(
        "SELECT
            strftime('%Y-%m-%d %H:00', timestamp) as hour,
            AVG(CAST(json_extract(metrics, '$.duration_ms') AS FLOAT)) as avg_latency
         FROM events
         WHERE service = 'forgeagents'
         AND event_type = 'agent_task_completed'
         AND datetime(timestamp) > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    )
    .bind(format!("-{}", hours))
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| TimeSeriesPoint {
        timestamp: row.get::<String, _>("hour"),
        value: row.get::<Option<f64>, _>("avg_latency").unwrap_or(0.0),
    })
    .collect();

    Ok(AgentLatencyOverTime { datapoints })
}

#[tauri::command]
async fn get_rake_metrics() -> Result<RakeMetrics, String> {
    let pool = get_db_pool().await?;

    // Get overall pipeline metrics
    let metrics = sqlx::query(
        "SELECT
            COUNT(DISTINCT json_extract(metrics, '$.pipeline_id')) as total_pipelines,
            COUNT(*) as records_ingested
         FROM events
         WHERE service = 'rake'
         AND event_type = 'ingestion_complete'"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?;

    let total_pipelines: i64 = metrics.get("total_pipelines");
    let records_ingested: i64 = metrics.get("records_ingested");

    // Calculate active pipelines (active in last hour)
    let active_pipelines = sqlx::query(
        "SELECT COUNT(DISTINCT json_extract(metrics, '$.pipeline_id')) as count
         FROM events
         WHERE service = 'rake'
         AND datetime(timestamp) > datetime('now', '-1 hour')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?
    .get::<i64, _>("count");

    // Calculate ingestion rate (records per hour)
    let ingestion_rate = sqlx::query(
        "SELECT COUNT(*) / 24.0 as rate
         FROM events
         WHERE service = 'rake'
         AND event_type = 'ingestion_complete'
         AND datetime(timestamp) > datetime('now', '-24 hours')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?
    .get::<Option<f64>, _>("rate")
    .unwrap_or(0.0);

    // Calculate error rate
    let error_rate = sqlx::query(
        "SELECT
            CAST(SUM(CASE WHEN severity = 'error' THEN 1 ELSE 0 END) AS FLOAT) /
            NULLIF(COUNT(*), 0) * 100.0 as error_rate
         FROM events
         WHERE service = 'rake'
         AND datetime(timestamp) > datetime('now', '-24 hours')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|e| e.to_string())?
    .get::<Option<f64>, _>("error_rate")
    .unwrap_or(0.0);

    // Get recent pipelines (top 5 by activity)
    let recent_pipelines = sqlx::query_as::<_, (String, String, String, i64, String)>(
        "SELECT
            COALESCE(json_extract(metrics, '$.pipeline_id'), 'unknown') as pipeline_id,
            COALESCE(json_extract(metrics, '$.pipeline_name'), 'Unknown Pipeline') as pipeline_name,
            CASE
                WHEN MAX(datetime(timestamp)) > datetime('now', '-1 hour') THEN 'active'
                ELSE 'idle'
            END as status,
            COUNT(*) as records_processed,
            MAX(timestamp) as last_run
         FROM events
         WHERE service = 'rake'
         GROUP BY pipeline_id
         ORDER BY records_processed DESC
         LIMIT 5"
    )
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|(pipeline_id, pipeline_name, status, records_processed, last_run)| PipelineInfo {
        pipeline_id,
        pipeline_name,
        status,
        records_processed,
        last_run,
    })
    .collect();

    Ok(RakeMetrics {
        total_pipelines,
        active_pipelines,
        records_ingested,
        ingestion_rate,
        error_rate,
        recent_pipelines,
    })
}

#[tauri::command]
async fn get_ingestion_over_time(hours: i64) -> Result<IngestionOverTime, String> {
    let pool = get_db_pool().await?;

    let datapoints: Vec<TimeSeriesPoint> = sqlx::query(
        "SELECT
            strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
            COUNT(*) as count
         FROM events
         WHERE service = 'rake'
         AND event_type = 'ingestion_complete'
         AND datetime(timestamp) > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    )
    .bind(format!("-{}", hours))
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| TimeSeriesPoint {
        timestamp: row.get::<String, _>("hour"),
        value: row.get::<i64, _>("count") as f64,
    })
    .collect();

    Ok(IngestionOverTime { datapoints })
}

#[tauri::command]
async fn get_error_rate_over_time(hours: i64) -> Result<ErrorRateOverTime, String> {
    let pool = get_db_pool().await?;

    let datapoints: Vec<TimeSeriesPoint> = sqlx::query(
        "SELECT
            strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
            CAST(SUM(CASE WHEN severity = 'error' THEN 1 ELSE 0 END) AS FLOAT) /
            NULLIF(COUNT(*), 0) * 100.0 as error_rate
         FROM events
         WHERE service = 'rake'
         AND datetime(timestamp) > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    )
    .bind(format!("-{}", hours))
    .fetch_all(&pool)
    .await
    .map_err(|e| e.to_string())?
    .into_iter()
    .map(|row| TimeSeriesPoint {
        timestamp: row.get::<String, _>("hour"),
        value: row.get::<Option<f64>, _>("error_rate").unwrap_or(0.0),
    })
    .collect();

    Ok(ErrorRateOverTime { datapoints })
}

// ===========================================================================
// Main
// ===========================================================================

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_system_health,
            get_recent_events,
            get_dataforge_metrics,
            get_neuroforge_metrics,
            get_cost_over_time,
            get_token_usage_over_time,
            get_search_performance_over_time,
            get_forgeagents_metrics,
            get_agent_activity_over_time,
            get_agent_latency_over_time,
            get_rake_metrics,
            get_ingestion_over_time,
            get_error_rate_over_time,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
