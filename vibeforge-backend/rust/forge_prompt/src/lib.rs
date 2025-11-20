use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Simple token estimation: ~4 characters = 1 token (naive approach)
#[pyfunction]
pub fn estimate_tokens(text: &str) -> u32 {
    (text.len() as f32 / 4.0).ceil() as u32
}

#[pyfunction]
pub fn estimate_tokens_precise(text: &str) -> u32 {
    // More realistic: count words and adjust
    let word_count = text.split_whitespace().count();
    let punctuation_count = text.matches(|c: char| c.is_ascii_punctuation()).count();
    (word_count as f32 * 1.3 + punctuation_count as f32 * 0.1).ceil() as u32
}

/// Build a final prompt from contexts and user prompt
#[pyfunction]
pub fn build_prompt(contexts: Vec<String>, prompt: String) -> String {
    let mut built = String::new();
    
    // Add context blocks
    if !contexts.is_empty() {
        built.push_str("# Context Information\n\n");
        for (i, ctx) in contexts.iter().enumerate() {
            if i > 0 {
                built.push_str("\n---\n\n");
            }
            built.push_str(ctx);
        }
        built.push_str("\n\n---\n\n");
    }
    
    // Add user prompt
    built.push_str("# Task\n\n");
    built.push_str(&prompt);
    
    built
}

/// Estimate tokens for a built prompt
#[pyfunction]
pub fn estimate_tokens_for_prompt(contexts: Vec<String>, prompt: String) -> u32 {
    let built = build_prompt(contexts, prompt);
    estimate_tokens_precise(&built)
}

/// Build initial run record as JSON string
#[pyfunction]
pub fn build_initial_run(model: String, prompt: String) -> String {
    use chrono::Utc;
    use uuid::Uuid;
    
    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true);
    
    let run = serde_json::json!({
        "id": id,
        "model": model,
        "prompt": prompt,
        "status": "pending",
        "output": null,
        "error": null,
        "tokens_used": null,
        "created_at": now,
        "started_at": null,
        "completed_at": null,
        "duration_ms": null,
    });
    
    serde_json::to_string(&run).unwrap_or_default()
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct PromptContext {
    #[pyo3(get, set)]
    pub system_prompt: String,
    #[pyo3(get, set)]
    pub user_prompt: String,
    #[pyo3(get, set)]
    pub context_blocks: Vec<String>,
    #[pyo3(get, set)]
    pub total_tokens_estimated: u32,
}

#[pymethods]
impl PromptContext {
    #[new]
    pub fn new(
        system_prompt: String,
        user_prompt: String,
    ) -> Self {
        let system_tokens = estimate_tokens_precise(&system_prompt);
        let user_tokens = estimate_tokens_precise(&user_prompt);
        
        PromptContext {
            system_prompt,
            user_prompt,
            context_blocks: Vec::new(),
            total_tokens_estimated: system_tokens + user_tokens,
        }
    }

    pub fn add_context(&mut self, context_text: String) {
        let context_tokens = estimate_tokens_precise(&context_text);
        self.context_blocks.push(context_text);
        self.total_tokens_estimated += context_tokens;
    }

    pub fn merge_contexts(&self) -> String {
        let mut merged = self.system_prompt.clone();
        merged.push_str("\n\n");
        
        for context in &self.context_blocks {
            merged.push_str("---\n");
            merged.push_str(context);
            merged.push_str("\n");
        }
        
        merged.push_str("\n---\n");
        merged.push_str(&self.user_prompt);
        
        merged
    }

    pub fn recalculate_tokens(&mut self) {
        let merged = self.merge_contexts();
        self.total_tokens_estimated = estimate_tokens_precise(&merged);
    }

    pub fn __repr__(&self) -> String {
        format!(
            "PromptContext(tokens={}, blocks={})",
            self.total_tokens_estimated,
            self.context_blocks.len()
        )
    }
}

#[pymodule]
fn forge_prompt(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(estimate_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(estimate_tokens_precise, m)?)?;
    m.add_function(wrap_pyfunction!(build_prompt, m)?)?;
    m.add_function(wrap_pyfunction!(estimate_tokens_for_prompt, m)?)?;
    m.add_function(wrap_pyfunction!(build_initial_run, m)?)?;
    m.add_class::<PromptContext>()?;
    Ok(())
}