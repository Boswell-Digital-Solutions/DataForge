# Dev Environment Guide (V2) — Full 15-Language Support  
### Mode: **Dev‑Container Only** for Kotlin, Swift, Dart

## Overview
This V2 document expands the Dev Environment Guide to cover **all 15 languages** supported in VibeForge’s Language Selector, with installation/detection guidance for Ubuntu/Pop!_OS and **Dev‑Container‑Only** workflows for mobile languages that cannot fully run on Linux.

VibeForge will:
- Detect runtimes locally  
- Warn when unsupported  
- Provide Dev Container scaffolding for mobile/complex SDKs  
- Never modify system paths  
- Never auto-install runtimes

---

# 1. Supported Languages (All 15)

## Frontend (3)
| Language | Runtime | Local Support | Notes |
|---------|----------|----------------|-------|
| JavaScript/TypeScript | Node.js | ✔️ Yes | Provided via Node |
| Svelte | Node.js | ✔️ Yes | Framework layer only |
| Solid | Node.js | ✔️ Yes | Framework layer only |

---

## Backend (5)
| Language | Runtime | Local Support | Notes |
|----------|----------|--------------|------|
| Python | CPython | ✔️ Yes | Python 3.x required |
| Node.js | Node | ✔️ Yes | JS/TS backend |
| Go | Go Toolchain | ✔️ Yes | Supported natively |
| Rust | Rust Toolchain | ✔️ Yes | Via rustup |
| Java | OpenJDK | ✔️ Yes | Via apt install |

---

## Systems / Tooling (4)
| Language | Runtime | Local Support | Notes |
|----------|----------|--------------|-------|
| C | GCC | ✔️ Yes | GNU toolchain |
| C++ | G++ | ✔️ Yes | GNU toolchain |
| Bash | Shell | ✔️ Yes | Native to Linux |
| SQL | Client tools | ✔️ Yes | `psql`, `sqlite3` etc |

---

## Mobile / Modern (3)
⚠️ These are **DEV-CONTAINER ONLY** for Linux hosts.

| Language | Runtime | Local Support | Status |
|----------|----------|--------------|--------|
| Dart | Flutter SDK | ⚠️ No | Dev‑container only |
| Kotlin | Android SDK + JVM | ⚠️ No | Dev‑container only |
| Swift | Swift Toolchain | ⚠️ Partial | Linux toolchain works but NOT iOS SDK → dev‑container only |

---

# 2. Local Runtime Detection

VibeForge’s Tauri backend will attempt to detect:

### Core Runtimes
```
node --version  
python3 --version  
rustc --version  
go version  
java -version  
gcc --version  
g++ --version  
psql --version  
```

### Mobile/Modern Runtimes
No local detection is attempted for:
- Flutter / Dart SDK
- Android SDK / Kotlin toolchain
- Swift iOS toolchain

These will always return:
```
Status: Dev‑Container Required
```

---

# 3. Dev‑Container Workflow (Option C)

When a user selects Dart/Kotlin/Swift:

VibeForge auto‑generates:

```
.devcontainer/devcontainer.json  
.devcontainer/Dockerfile  
```

### Example Dev Container (Full SDKs Included)

```json
{
  "name": "VibeForge Mobile Dev",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "lts" },
    "ghcr.io/devcontainers/features/java:1": { "version": "17" },
    "ghcr.io/devcontainers/features/android:1": {},
    "ghcr.io/devcontainers/features/flutter:1": {}
  }
}
```

### Notes
- Flutter + Android SDK + Kotlin CLI run cleanly inside devcontainers
- Swift Linux toolchain builds server‑side Swift apps, not iOS apps
- iOS builds remain macOS‑only → container cannot solve this

---

# 4. Local Installation Commands (for supported runtimes)

### Node.js
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

### Python 3
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### Rust
```bash
curl https://sh.rustup.rs -sSf | sh
```

### Go
```bash
sudo snap install go --classic
```

### Java
```bash
sudo apt install -y default-jdk
```

### C / C++
```bash
sudo apt install -y build-essential
```

### SQL Clients
```bash
sudo apt install -y postgresql-client sqlite3
```

---

# 5. Toolchains Panel (Local Configuration)

Users can set manual paths:

```json
{
  "node": "/usr/bin/node",
  "python": "/usr/bin/python3",
  "rust": "/home/user/.cargo/bin/rustc",
  "go": "/snap/bin/go",
  "java": "/usr/bin/java",
  "gcc": "/usr/bin/gcc",
  "gpp": "/usr/bin/g++"
}
```

Mobile toolchains do **not** appear here—they are container-only.

---

# 6. Wizard Behavior with Mobile Languages

If user selects:

- Dart  
- Kotlin  
- Swift  

Wizard shows:

> “This language requires SDKs not supported on Linux hosts.  
> VibeForge will create a **Dev Container** to support this environment.”

Options:

- ✔️ Generate Dev Container  
- ✔️ Continue anyway  
- ℹ️ Learn More (opens docs)

---

# 7. Dev Diagnostics Panel

Status overview example:

| Runtime | Version | Status |
|--------|---------|--------|
| Node.js | v22.x | ✔️ Installed |
| Python | 3.11 | ✔️ Installed |
| Rust | 1.76 | ✔️ Installed |
| Go | 1.22 | ✔️ Installed |
| Java | 17 | ✔️ Installed |
| C/C++ | GCC 12 | ✔️ Installed |
| Dart | — | 🐳 Dev‑Container Required |
| Kotlin | — | 🐳 Dev‑Container Required |
| Swift | — | 🐳 Dev‑Container Required |

Legend:

- ✔️ = Host runtime available  
- 🐳 = Dev‑Container runtime  

---

# 8. Philosophy

VibeForge is:

- **Local-first**
- **Linux-first**
- **Non-invasive**
- **Transparent**
- **Developer‑respecting**

Mobile dev on Linux is container-only by design to avoid instability, unsupported builds, and SDK conflicts.

---

# End of Document
