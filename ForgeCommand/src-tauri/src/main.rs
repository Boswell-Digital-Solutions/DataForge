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

    // Calculate uptime (% of successful vs total events in last 24h)
    let dataforge_uptime = calculate_uptime(&pool, "dataforge").await?;
    let neuroforge_uptime = calculate_uptime(&pool, "neuroforge").await?;

    Ok(SystemHealth {
        dataforge_status: if dataforge_recent > 0 { "UP".to_string() } else { "DOWN".to_string() },
        dataforge_uptime,
        neuroforge_status: if neuroforge_recent > 0 { "UP".to_string() } else { "DOWN".to_string() },
        neuroforge_uptime,
        rake_status: "NOT_DEPLOYED".to_string(),
        rake_uptime: 0.0,
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
            AVG(CAST(json_extract(metrics, '$.model_latency_ms') AS FLOAT)) as avg_latency
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
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
