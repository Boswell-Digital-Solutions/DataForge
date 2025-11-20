use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Evaluation score structure
#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct Score {
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub value: f32,
    #[pyo3(get, set)]
    pub scale: String, // "1-5", "1-10", "0-1"
}

#[pymethods]
impl Score {
    #[new]
    pub fn new(name: String, value: f32, scale: String) -> Self {
        Score { name, value, scale }
    }

    pub fn is_valid(&self) -> bool {
        match self.scale.as_str() {
            "1-5" => self.value >= 1.0 && self.value <= 5.0,
            "1-10" => self.value >= 1.0 && self.value <= 10.0,
            "0-1" => self.value >= 0.0 && self.value <= 1.0,
            _ => false,
        }
    }

    pub fn __repr__(&self) -> String {
        format!("Score({}={}/{})", self.name, self.value, self.scale)
    }
}

/// Evaluation result
#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct Evaluation {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub run_id: String,
    #[pyo3(get, set)]
    pub evaluator: String,
    #[pyo3(get, set)]
    pub scores: Vec<(String, f32)>, // Stored as tuples
    #[pyo3(get, set)]
    pub notes: String,
    #[pyo3(get, set)]
    pub created_at: String, // ISO 8601
}

#[pymethods]
impl Evaluation {
    #[new]
    pub fn new(run_id: String, evaluator: String) -> Self {
        Evaluation {
            id: uuid::Uuid::new_v4().to_string(),
            run_id,
            evaluator,
            scores: Vec::new(),
            notes: String::new(),
            created_at: chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
        }
    }

    pub fn add_score(&mut self, name: String, value: f32) {
        self.scores.push((name, value));
    }

    pub fn average_score(&self) -> f32 {
        if self.scores.is_empty() {
            return 0.0;
        }
        let sum: f32 = self.scores.iter().map(|(_, v)| v).sum();
        sum / self.scores.len() as f32
    }

    pub fn __repr__(&self) -> String {
        format!(
            "Evaluation(run_id={}, avg_score={:.2})",
            self.run_id,
            self.average_score()
        )
    }
}

/// Stub for sweep configuration
#[pyfunction]
pub fn create_sweep(name: String, param_grid: Vec<String>) -> String {
    format!(
        "Sweep({}, params={:?}) - stub implementation",
        name, param_grid
    )
}

#[pymodule]
fn forge_eval(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Score>()?;
    m.add_class::<Evaluation>()?;
    m.add_function(wrap_pyfunction!(create_sweep, m)?)?;
    Ok(())
}
