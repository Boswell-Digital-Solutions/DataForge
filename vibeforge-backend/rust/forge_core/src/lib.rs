use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct TokenUsage {
    #[pyo3(get, set)]
    pub prompt_tokens: u32,
    #[pyo3(get, set)]
    pub completion_tokens: u32,
    #[pyo3(get, set)]
    pub total_tokens: u32,
}

#[pymethods]
impl TokenUsage {
    #[new]
    pub fn new(prompt_tokens: u32, completion_tokens: u32, total_tokens: u32) -> Self {
        TokenUsage {
            prompt_tokens,
            completion_tokens,
            total_tokens,
        }
    }

    pub fn __repr__(&self) -> String {
        format!(
            "TokenUsage(prompt={}, completion={}, total={})",
            self.prompt_tokens, self.completion_tokens, self.total_tokens
        )
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[pyclass]
pub enum RunStatus {
    #[default]
    Pending,
    Running,
    Complete,
    Error,
    Cancelled,
}

#[pymethods]
impl RunStatus {
    pub fn __repr__(&self) -> String {
        match self {
            RunStatus::Pending => "RunStatus.Pending".to_string(),
            RunStatus::Running => "RunStatus.Running".to_string(),
            RunStatus::Complete => "RunStatus.Complete".to_string(),
            RunStatus::Error => "RunStatus.Error".to_string(),
            RunStatus::Cancelled => "RunStatus.Cancelled".to_string(),
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct ModelRun {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub workspace_id: String,
    #[pyo3(get, set)]
    pub model: String,
    #[pyo3(get, set)]
    pub prompt: String,
    #[pyo3(get, set)]
    pub status: String, // "pending" | "running" | "complete" | "error" | "cancelled"
    #[pyo3(get, set)]
    pub output: Option<String>,
    #[pyo3(get, set)]
    pub error: Option<String>,
    #[pyo3(get, set)]
    pub tokens_used: Option<(u32, u32, u32)>, // (prompt, completion, total)
    #[pyo3(get, set)]
    pub created_at: String, // ISO 8601
    #[pyo3(get, set)]
    pub started_at: Option<String>,
    #[pyo3(get, set)]
    pub completed_at: Option<String>,
    #[pyo3(get, set)]
    pub duration_ms: Option<u64>,
    #[pyo3(get, set)]
    pub context_ids: Vec<String>,
    #[pyo3(get, set)]
    pub model_config: Option<String>, // JSON string
    #[pyo3(get, set)]
    pub tags: Vec<String>,
}

#[pymethods]
impl ModelRun {
    #[new]
    pub fn new(
        workspace_id: String,
        model: String,
        prompt: String,
    ) -> Self {
        let id = Uuid::new_v4().to_string();
        let now = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
        
        ModelRun {
            id,
            workspace_id,
            model,
            prompt,
            status: "pending".to_string(),
            output: None,
            error: None,
            tokens_used: None,
            created_at: now,
            started_at: None,
            completed_at: None,
            duration_ms: None,
            context_ids: Vec::new(),
            model_config: None,
            tags: Vec::new(),
        }
    }

    pub fn __repr__(&self) -> String {
        format!(
            "ModelRun(id={}, model={}, status={})",
            self.id, self.model, self.status
        )
    }

    pub fn to_dict(&self) -> PyResult<String> {
        Ok(serde_json::to_string(self).unwrap_or_default())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct ContextBlock {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub title: String,
    #[pyo3(get, set)]
    pub kind: String, // "system" | "design" | "project" | "code" | "workflow"
    #[pyo3(get, set)]
    pub description: String,
    #[pyo3(get, set)]
    pub tags: Vec<String>,
    #[pyo3(get, set)]
    pub content: String,
    #[pyo3(get, set)]
    pub is_active: bool,
    #[pyo3(get, set)]
    pub last_updated: String, // ISO 8601
    #[pyo3(get, set)]
    pub source: String, // "global" | "workspace" | "local"
}

#[pymethods]
impl ContextBlock {
    #[new]
    pub fn new(
        title: String,
        kind: String,
        description: String,
        content: String,
        source: String,
    ) -> Self {
        let id = Uuid::new_v4().to_string();
        let now = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
        
        ContextBlock {
            id,
            title,
            kind,
            description,
            tags: Vec::new(),
            content,
            is_active: false,
            last_updated: now,
            source,
        }
    }

    pub fn __repr__(&self) -> String {
        format!("ContextBlock(id={}, title={})", self.id, self.title)
    }
}

#[pymodule]
fn forge_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TokenUsage>()?;
    m.add_class::<RunStatus>()?;
    m.add_class::<ModelRun>()?;
    m.add_class::<ContextBlock>()?;
    Ok(())
}
