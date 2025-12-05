# CLAUDE INTEGRATION - SETUP GUIDE

**Purpose:** How to use Claude effectively with the Forge Ecosystem project  
**Last Updated:** December 3, 2025

---

## 📦 WHAT YOU JUST DOWNLOADED

You have **4 essential files** for Claude integration:

1. **`.claude_project_context.md`** - Complete project context
2. **`CLAUDE_CUSTOM_INSTRUCTIONS.md`** - Instructions for how Claude should behave
3. **`.vscode-settings.json`** - VS Code workspace settings
4. **`CLAUDE_INTEGRATION_README.md`** - This file

---

## 🚀 QUICK START

### Step 1: Place the Files

```bash
# Navigate to your Forge project root
cd /path/to/forge-ecosystem

# Create .vscode directory if it doesn't exist
mkdir -p .vscode

# Move the files
mv /tmp/.claude_project_context.md ./
mv /tmp/CLAUDE_CUSTOM_INSTRUCTIONS.md ./
mv /tmp/.vscode-settings.json ./.vscode/settings.json

# Verify placement
ls -la | grep claude
# Should see: .claude_project_context.md, CLAUDE_CUSTOM_INSTRUCTIONS.md

ls .vscode/
# Should see: settings.json
```

### Step 2: Update Your .gitignore

Add to your `.gitignore`:
```bash
# Local development files
.env.local
*.local

# Keep Claude context files in repo
# (they don't contain secrets, just project context)
!.claude_project_context.md
!CLAUDE_CUSTOM_INSTRUCTIONS.md
```

### Step 3: Open in VS Code

```bash
# Open the project
code .

# VS Code will automatically use the settings.json
```

---

## 🎯 HOW TO USE WITH CLAUDE

### Option 1: Claude.ai Web Interface (Recommended for Planning)

**For high-level discussions, architecture decisions, documentation:**

1. **Start a new conversation** with Claude
2. **Upload the context file:**
   - Click the 📎 attachment button
   - Select `.claude_project_context.md`
3. **Reference in your questions:**
   ```
   [After uploading context]
   "Based on the Forge context, help me design the Rake fetch stage for SEC EDGAR filings"
   ```

**Pro Tip:** Upload both context files together:
- `.claude_project_context.md` (what the project is)
- `CLAUDE_CUSTOM_INSTRUCTIONS.md` (how Claude should help)

### Option 2: Claude for VS Code Extension

**For in-editor coding assistance:**

1. **Install:** [Claude for VS Code](https://marketplace.visualstudio.com/items?itemName=anthropic.claude-for-vscode) (if available)

2. **Configure:** The `.vscode/settings.json` already includes:
   ```json
   "claude.contextFiles": [
     ".claude_project_context.md",
     "CLAUDE_CUSTOM_INSTRUCTIONS.md",
     "FORGE_COMMAND_IMPLEMENTATION_DECISIONS.md",
     "README.md"
   ]
   ```

3. **Use:** Right-click in editor → "Ask Claude" → Claude has full context

### Option 3: Claude Desktop App (Recommended for Coding)

**For deep coding sessions with full filesystem access:**

1. **Open Claude Desktop**
2. **Create a Project** named "Forge Ecosystem"
3. **Add Project Knowledge:**
   - Add `.claude_project_context.md`
   - Add `CLAUDE_CUSTOM_INSTRUCTIONS.md`
   - Add `FORGE_COMMAND_IMPLEMENTATION_DECISIONS.md`
   - Add any Stage documents you're working with
4. **Start coding conversations**

**Advantage:** Claude can read all project files directly

---

## 💡 EXAMPLE INTERACTIONS

### 🎨 When Designing Features

**Good Question:**
```
I need to add telemetry to the DataForge query endpoint at app/api/v1/vector_router.py.

Can you show me:
1. How to emit a 'query' event with latency metrics
2. How to propagate correlation_id from the request
3. Error event emission if the query fails
4. Unit tests to verify telemetry

Use the DataForge blue color scheme when showing me how this appears in Command Central.
```

**Claude will:**
- Read `.claude_project_context.md` for telemetry schema
- Follow `CLAUDE_CUSTOM_INSTRUCTIONS.md` for code style
- Use correct blue color (#00A3FF) for DataForge
- Include complete, runnable code
- Add telemetry emission
- Provide tests

### 🐛 When Debugging

**Good Question:**
```
I'm seeing this error in Rake:

  File "rake/pipeline/fetch.py", line 45
  TypeError: 'NoneType' object is not iterable

The job_started event IS being emitted, but job_completed is NOT.
I suspect the fetch stage is failing silently.

Help me debug this and add proper error event emission.
```

**Claude will:**
- Diagnose the issue (likely missing error handling)
- Show how to add try/except with telemetry
- Emit job_failed event on errors
- Test the fix

### 🏗️ When Building New Features

**Good Question:**
```
I need to build the Rake clean stage (pipeline/clean.py).

Requirements:
- Remove HTML tags
- Normalize whitespace
- Filter out documents < 100 words
- Emit phase_completed event with timing
- Handle errors gracefully

Show me the complete implementation with tests.
```

**Claude will:**
- Provide complete `clean.py` implementation
- Include telemetry emission
- Add correlation_id propagation
- Show error handling
- Include unit tests
- Explain how it integrates with orchestrator

---

## 📚 CONTEXT FILE GUIDE

### When to Reference Each File

**`.claude_project_context.md`**
- Quick overview of all services
- Architecture decisions summary
- Brand colors reference
- Development environment setup
- Current implementation status

**`CLAUDE_CUSTOM_INSTRUCTIONS.md`**
- How to write Python/Rust/TypeScript code
- Telemetry integration patterns
- Testing requirements
- Communication style
- Security reminders

**`FORGE_COMMAND_IMPLEMENTATION_DECISIONS.md`**
- Deep dive on architectural decisions
- Why we chose Tauri over web
- Why shared database over separate
- Complete telemetry event schemas
- 4-week implementation roadmap

**`RAKE_DEVELOPMENT_GUIDE.md`**
- Complete Rake implementation guide
- Pipeline stage details
- Source adapter examples
- Scheduling and automation
- Command Central integration

---

## 🎓 BEST PRACTICES

### 1. Start Every Session with Context

**First message to Claude:**
```
I'm working on the Forge Ecosystem. I've uploaded .claude_project_context.md 
and CLAUDE_CUSTOM_INSTRUCTIONS.md. 

Today I'm working on [specific feature]. Ready to start?
```

### 2. Reference Specific Documents

**When asking questions:**
```
According to FORGE_COMMAND_IMPLEMENTATION_DECISIONS.md, we're using a shared 
database. How should I structure the events table migration?
```

### 3. Specify the Service

**Always mention which service:**
```
For DataForge (not NeuroForge), I need to...
```

### 4. Include Current Code

**For debugging:**
```
Here's my current fetch.py:

[paste code]

It's not emitting telemetry. Can you fix it?
```

### 5. Ask for Complete Solutions

**Don't ask for snippets:**
```
❌ "Show me how to use asyncio"
✅ "Show me the complete async fetch_stage() function with telemetry for Rake"
```

---

## 🔄 KEEPING CONTEXT UPDATED

### When to Update Context Files

**Update `.claude_project_context.md` when:**
- Major features are completed
- Architecture decisions change
- New services are added
- Implementation status changes

**Update `CLAUDE_CUSTOM_INSTRUCTIONS.md` when:**
- Coding standards evolve
- New patterns emerge
- Common mistakes are identified
- Best practices change

### How to Update

1. **Edit the file** with new information
2. **Commit to git** (these aren't secrets)
3. **Re-upload** to Claude in your next session

```bash
git add .claude_project_context.md
git commit -m "docs: update context - DataForge telemetry complete"
git push
```

---

## 🎨 VS CODE CUSTOMIZATION

### The settings.json Includes:

**Python:**
- Black formatting (line length 100)
- mypy strict type checking
- pytest test runner
- Import organization on save

**Rust:**
- Clippy linting
- rust-analyzer for completions
- Format on save

**TypeScript/Svelte:**
- Prettier formatting
- Tailwind CSS IntelliSense
- Svelte syntax support

**Database:**
- SQLTools connection to DataForge
- SQL syntax highlighting

**Color Theme:**
- Bracket colors match Forge services:
  - Level 1: DataForge Blue (#00A3FF)
  - Level 2: NeuroForge Violet (#A855F7)
  - Level 3: Rake Cyan (#2DD4BF)
  - Level 4: Forge Ember (#D97706)

### Recommended Extensions

Install these VS Code extensions:
```bash
# Python
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance

# Rust (for Tauri)
code --install-extension rust-lang.rust-analyzer

# Web (for SvelteKit)
code --install-extension svelte.svelte-vscode
code --install-extension bradlc.vscode-tailwindcss

# Database
code --install-extension mtxr.sqltools
code --install-extension mtxr.sqltools-driver-pg

# Utilities
code --install-extension esbenp.prettier-vscode
code --install-extension streetsidesoftware.code-spell-checker
code --install-extension Gruntfuggly.todo-tree

# Claude Integration (if available)
code --install-extension anthropic.claude-for-vscode
```

---

## 🚨 TROUBLESHOOTING

### "Claude doesn't remember our conversation"

**Solution:** Claude.ai web has conversation history, but each new chat is independent.
- Use Claude Projects (desktop app) for persistent context
- Re-upload context files for each new web conversation

### "Claude gives me generic Python, not Forge-specific code"

**Solution:** You didn't upload the context files or didn't reference them.
```
❌ "Write a Python function to fetch data"
✅ "Based on .claude_project_context.md, write a Rake fetch stage with telemetry"
```

### "Code doesn't match our conventions"

**Solution:** Explicitly reference the custom instructions:
```
"Following CLAUDE_CUSTOM_INSTRUCTIONS.md, write this with:
- Type hints
- Telemetry emission
- Parameterized SQL
- Unit tests"
```

### "Claude suggests wrong architecture"

**Solution:** Point to the decisions document:
```
"According to FORGE_COMMAND_IMPLEMENTATION_DECISIONS.md, we're using 
a Tauri desktop app, not a web app. Please revise your suggestion."
```

---

## 📊 MEASURING EFFECTIVENESS

### Good Indicators:

✅ **Code runs without modification**
- Claude understands the architecture
- Follows project conventions
- Includes necessary imports

✅ **Telemetry events appear in database**
- Claude remembers to emit events
- Correlation IDs are included
- Metrics are tracked

✅ **Tests pass on first try**
- Claude writes working tests
- Covers edge cases
- Verifies telemetry

✅ **Matches brand guidelines**
- Correct service colors
- Dark mode compatible
- Mission-control aesthetic

### Needs Improvement:

❌ **Code requires debugging before running**
- Missing imports
- Syntax errors
- Type mismatches

❌ **Missing telemetry integration**
- No event emission
- No correlation IDs
- No metrics tracking

❌ **Wrong colors or design**
- Blue for NeuroForge (should be violet)
- Light mode code (should be dark)
- Generic dashboard design

---

## 🎯 QUICK REFERENCE CARD

### 🟦 DataForge Questions
- Color: Blue (#00A3FF)
- Port: 8001
- Status: Production, needs telemetry
- Context: Vector memory engine

### 🟪 NeuroForge Questions  
- Color: Violet (#A855F7)
- Port: 8000
- Status: Production, needs telemetry
- Context: LLM orchestration

### 🟦 Rake Questions
- Color: Cyan (#2DD4BF)
- Port: 8002
- Status: In development, greenfield
- Context: Ingestion pipeline

### 🖥️ Forge Command Questions
- Type: Tauri desktop app
- Status: Planning complete, ready to build
- Context: Unified observability

### 📊 Telemetry Questions
- Schema: events table in DataForge DB
- Fields: service, event_type, correlation_id, metadata, metrics
- Pattern: emit on start, success, failure

---

## 📞 SUPPORT

If you have questions about using Claude with this project:

1. **Check** `.claude_project_context.md` for context
2. **Check** `CLAUDE_CUSTOM_INSTRUCTIONS.md` for patterns
3. **Check** implementation decision docs for "why"
4. **Ask Claude** with specific context
5. **Iterate** based on responses

---

**Remember:** Good context = Good code. Always upload `.claude_project_context.md` at the start of each session!

---

**Last Updated:** December 3, 2025  
**Guide Version:** 1.0  
**Project:** Forge Ecosystem

Happy coding! 🚀
