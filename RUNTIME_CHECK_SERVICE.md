# Tauri Runtime Check Service — Design Sketch

## Overview

The Runtime Check Service is a small Tauri backend module that:

- Detects installed runtimes (Node, Python, Rust, Go, Java, etc.).
- Uses the system PATH and optional user-configured paths.
- Returns a structured JSON response to the SvelteKit frontend.
- Powers:
  - The Language/Stack Wizard validation
  - The Dev Environment / Diagnostics panel
  - “Missing runtime” warnings and guidance

This document sketches the design and a rough implementation outline.

---

## 1. Responsibilities

- Run non-blocking checks for each configured runtime.
- Normalize version output (string parsing).
- Merge system PATH detection with user-specified overrides.
- Cache results for a short time to avoid spamming the system.
- Expose a Tauri command callable from the frontend.

It does **not**:

- Install any runtimes.
- Modify PATH.
- Run long-running or destructive commands.

---

## 2. Data Model

### 2.1 RuntimeStatus

```ts
type RuntimeStatus = {
  id: string;                 // "node", "python", "rust", "go", "java", etc.
  name: string;               // "Node.js", "Python 3", ...
  required: boolean;          // whether this runtime is required for current project
  installed: boolean;         // true if found
  on_path: boolean;           // true if detected via PATH
  version: string | null;     // parsed version string
  path: string | null;        // resolved binary path, if known
  last_checked: string | null;// ISO timestamp
  notes?: string;             // optional additional info
};
```

### 2.2 RuntimeCheckResult

```ts
type RuntimeCheckResult = {
  runtimes: RuntimeStatus[];
};
```

The frontend will render this structure in the Wizard and Dev Environment panels.

---

## 3. Config: Known Runtimes

Define a simple static (or config-driven) list of known runtimes in Rust:

```rust
pub struct RuntimeConfig {
    pub id: &'static str,
    pub name: &'static str,
    pub default_cmd: &'static str, // e.g. "node", "python3", "rustc"
}

pub const KNOWN_RUNTIMES: &[RuntimeConfig] = &[
    RuntimeConfig { id: "node",   name: "Node.js",   default_cmd: "node" },
    RuntimeConfig { id: "python", name: "Python 3",  default_cmd: "python3" },
    RuntimeConfig { id: "rust",   name: "Rust",      default_cmd: "rustc" },
    RuntimeConfig { id: "go",     name: "Go",        default_cmd: "go" },
    RuntimeConfig { id: "java",   name: "Java",      default_cmd: "java" },
];
```

Later you can make this configurable or load from a TOML/JSON file.

---

## 4. User Config Overrides

You may keep a small JSON config on disk, e.g. at:

- `~/.vibeforge/toolchains.json` or
- in Tauri’s app config directory.

Example:

```json
{
  "node": "/home/charles/.nvm/versions/node/v22.0.0/bin/node",
  "python": "/usr/bin/python3",
  "rust": "/home/charles/.cargo/bin/rustc",
  "go": "/snap/bin/go"
}
```

The runtime check service will:

1. Check if there is a user override for a runtime.
2. If yes, attempt to run that path with `--version` or equivalent.
3. If no, fall back to the default command (`node`, `python3`, etc.).

---

## 5. Tauri Command Sketch

In `src-tauri/src/main.rs` or a separate module, define a command:

```rust
use serde::Serialize;
use std::process::Command;
use chrono::{DateTime, Utc};

#[derive(Serialize)]
struct RuntimeStatus {
    id: String,
    name: String,
    required: bool,
    installed: bool,
    on_path: bool,
    version: Option<String>,
    path: Option<String>,
    last_checked: Option<String>,
    notes: Option<String>,
}

#[derive(Serialize)]
struct RuntimeCheckResult {
    runtimes: Vec<RuntimeStatus>,
}

#[tauri::command]
async fn check_runtimes() -> Result<RuntimeCheckResult, String> {
    // TODO: load user config (toolchains.json)
    // let config = load_toolchains_config()?;

    let mut results = Vec::new();

    for rt in crate::runtime_config::KNOWN_RUNTIMES {
        let now: DateTime<Utc> = Utc::now();

        // Resolve command: user override or default
        // let cmd_path = resolve_runtime_path(rt.id, &config).unwrap_or(rt.default_cmd.to_string());
        let cmd_path = rt.default_cmd.to_string();

        let mut status = RuntimeStatus {
            id: rt.id.to_string(),
            name: rt.name.to_string(),
            required: false, // can be flagged by frontend later
            installed: false,
            on_path: true,
            version: None,
            path: None,
            last_checked: Some(now.to_rfc3339()),
            notes: None,
        };

        // Try `<cmd> --version` or `java -version`
        let output = if rt.id == "java" {
            Command::new(&cmd_path)
                .arg("-version")
                .output()
        } else {
            Command::new(&cmd_path)
                .arg("--version")
                .output()
        };

        match output {
            Ok(out) => {
                if out.status.success() {
                    status.installed = true;
                    // Try to decode either stdout or stderr (Java prints to stderr)
                    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
                    let stderr = String::from_utf8_lossy(&out.stderr).to_string();
                    let combined = if !stdout.trim().is_empty() { stdout } else { stderr };

                    status.version = extract_version_from_output(&combined);
                    status.path = Some(cmd_path);
                } else {
                    status.notes = Some("Command executed but returned non-zero exit code".into());
                }
            }
            Err(err) => {
                status.installed = false;
                status.on_path = false;
                status.notes = Some(format!("Failed to run {}: {}", cmd_path, err));
            }
        }

        results.push(status);
    }

    Ok(RuntimeCheckResult { runtimes: results })
}

// Stub version parser – later, implement more robust parsing per runtime
fn extract_version_from_output(output: &str) -> Option<String> {
    // very naive: first token that looks like a semver-ish thing
    for token in output.split_whitespace() {
        if token.chars().any(|c| c.is_ascii_digit()) {
            return Some(token.trim().to_string());
        }
    }
    None
}
```

Then register the command in Tauri:

```rust
fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            check_runtimes,
            // other commands...
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

---

## 6. Frontend Integration (SvelteKit via Tauri)

On the frontend (Svelte):

```ts
import { invoke } from '@tauri-apps/api/tauri';

export type RuntimeStatus = {
  id: string;
  name: string;
  required: boolean;
  installed: boolean;
  on_path: boolean;
  version: string | null;
  path: string | null;
  last_checked: string | null;
  notes?: string;
};

export type RuntimeCheckResult = {
  runtimes: RuntimeStatus[];
};

export async function fetchRuntimeStatus(): Promise<RuntimeCheckResult> {
  const result = await invoke<RuntimeCheckResult>('check_runtimes');
  return result;
}
```

In a Svelte component:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import type { RuntimeCheckResult } from '$lib/runtime-check';

  let data: RuntimeCheckResult | null = null;
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    try {
      data = await fetchRuntimeStatus();
    } catch (err) {
      error = String(err);
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <p>Checking local runtimes…</p>
{:else if error}
  <p class="text-red-500">Error: {error}</p>
{:else if data}
  <table>
    <thead>
      <tr>
        <th>Runtime</th>
        <th>Status</th>
        <th>Version</th>
        <th>Path</th>
      </tr>
    </thead>
    <tbody>
      {#each data.runtimes as rt}
        <tr>
          <td>{rt.name}</td>
          <td>{rt.installed ? 'Installed' : 'Missing'}</td>
          <td>{rt.version ?? '—'}</td>
          <td>{rt.path ?? '—'}</td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}
```

You can reuse this in:

- Project Wizard summary
- Dev Environment / Diagnostics panel
- Toolchains settings (with additional controls)

---

## 7. Caching Strategy (Optional)

To avoid re-running checks constantly:

- Cache the last `RuntimeCheckResult` + timestamp in memory or on disk.
- Reuse it if:
  - last check < N seconds/minutes ago
- Allow a **“Re-check”** button in the UI that forces a refresh.

Pseudo‑logic:

```rust
// If last_check_timestamp is within 60 seconds, return cached result.
// Otherwise re-run checks and update cache.
```

---

## 8. Security & Safety Considerations

- Only execute **well‑known binaries** (from config or known defaults).
- Do not execute arbitrary user-provided shell commands.
- Never run as root or with escalated privileges.
- Provide clear error messages if a runtime path is invalid.

---

## 9. Future Enhancements

- Per‑project runtime requirements (mark some runtimes as `required: true`).
- Integration with Dev Container generation (if required runtimes are missing).
- Mapping language selections → required runtime checks.
- More robust version parsing per runtime.
- Extended runtime support (Dart, Kotlin, Swift, etc.).

---

# End of Document
