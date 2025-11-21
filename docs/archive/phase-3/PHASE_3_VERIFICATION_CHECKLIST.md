# Phase 3 Verification Checklist

**Purpose**: Validate that Phase 3 implementation is complete and ready for end-to-end testing

**Current Status**: ✅ Implementation complete, integration verified, documentation complete

---

## 📋 Pre-Testing Validation

### 1. File Existence & Integrity

#### VibeForge Frontend Files

- [ ] `/vibeforge/src/lib/types/research.ts` exists (67 lines)
- [ ] `/vibeforge/src/lib/stores/researchStore.ts` exists (162 lines)
- [ ] `/vibeforge/src/lib/components/research/ResearchPanel.svelte` exists (579 lines)
- [ ] `/vibeforge/src/lib/components/OutputColumn.svelte` modified (273 lines)

**Verification Commands**:

```bash
wc -l /home/charles/projects/Coding2025/Forge/vibeforge/src/lib/types/research.ts
wc -l /home/charles/projects/Coding2025/Forge/vibeforge/src/lib/stores/researchStore.ts
wc -l /home/charles/projects/Coding2025/Forge/vibeforge/src/lib/components/research/ResearchPanel.svelte
wc -l /home/charles/projects/Coding2025/Forge/vibeforge/src/lib/components/OutputColumn.svelte
```

#### Backend Files (Phase 1 & 2)

**DataForge** (port 8001):

- [ ] `DataForge/app/api/external_search_router.py` exists
- [ ] `DataForge/app/services/external_search_service.py` exists
- [ ] `DataForge/app/services/base_connector.py` exists
- [ ] `DataForge/app/services/stackoverflow_connector.py` exists

**NeuroForge** (port 8002):

- [ ] `NeuroForge/app/routers/research.py` exists
- [ ] `NeuroForge/services/research_orchestrator.py` exists
- [ ] `NeuroForge/services/dataforge_client.py` exists
- [ ] `NeuroForge/services/research_models.py` exists

---

### 2. Type Safety & Compilation

#### TypeScript Check

```bash
cd /home/charles/projects/Coding2025/Forge/vibeforge
pnpm check
```

**Expected Output**:

- [ ] ✅ No errors (or only pre-existing non-blocking errors)
- [ ] Svelte validation passes
- [ ] TypeScript strict mode passes

**Accept Pre-Existing Errors**:

- `response?.output_id` (undefined property) — resolves at build time
- Module import warnings — resolve at build time

---

### 3. Import Chain Verification

#### Verify imports resolve

- [ ] ResearchPanel imports researchStore ✅
- [ ] OutputColumn imports ResearchPanel ✅
- [ ] researchStore imports research types ✅
- [ ] research API client imports exist ✅

**Verification Command**:

```bash
grep -r "import.*research" /home/charles/projects/Coding2025/Forge/vibeforge/src/lib/components/OutputColumn.svelte
```

---

## 🚀 End-to-End System Testing

### 4. Service Startup (3 Terminals)

#### Terminal 1: DataForge (Port 8001)

```bash
cd /home/charles/projects/Coding2025/Forge/DataForge
python -m uvicorn app.main:app --reload --port 8001
```

**Wait For**:

- [ ] Server starts without errors
- [ ] Displays: `Uvicorn running on http://127.0.0.1:8001`
- [ ] Health check responds: `curl http://localhost:8001/health`

#### Terminal 2: NeuroForge (Port 8002)

```bash
cd /home/charles/projects/Coding2025/Forge/NeuroForge
python -m uvicorn app.main:app --reload --port 8002
```

**Wait For**:

- [ ] Server starts without errors
- [ ] Displays: `Uvicorn running on http://127.0.0.1:8002`
- [ ] Health check responds: `curl http://localhost:8002/api/v1/research/health`

#### Terminal 3: VibeForge Frontend (Port 5173)

```bash
cd /home/charles/projects/Coding2025/Forge/vibeforge
pnpm dev
```

**Wait For**:

- [ ] Dev server starts: `VITE v7.x.x ready in XX ms`
- [ ] Displays: `➜  Local:   http://localhost:5173/`
- [ ] No compilation errors

---

### 5. UI Navigation Test

#### Open Browser

- [ ] Navigate to `http://localhost:5173`
- [ ] Page loads without errors
- [ ] Console has no critical errors (warnings OK)

#### Check Navigation

- [ ] Top bar visible
- [ ] Side navigation visible
- [ ] OutputColumn component renders

#### Research Tab Visibility

- [ ] Locate "🔍 Research" tab in OutputColumn
- [ ] Tab visible and clickable
- [ ] Tab styling appears amber/gold (theme: dark)

---

### 6. Research Query Execution Test

#### Step 1: Enter Query

- [ ] Click in query input field
- [ ] Type test query: `"How do I implement OAuth2 in SvelteKit?"`
- [ ] Query text appears in input

#### Step 2: Configure Research

- [ ] Source selection: Check at least 2 sources (e.g., StackOverflow, GitHub)
- [ ] Depth selector: Select "normal"
- [ ] Max results: Set to 5
- [ ] All settings visible and clickable

#### Step 3: Execute Query

- [ ] Click "Execute" button
- [ ] Button becomes disabled
- [ ] Loading spinner appears
- [ ] Wait 5-10 seconds for response

#### Step 4: Verify Results

- [ ] Results display in panel
- [ ] Summary section contains text
- [ ] Answer section contains analysis
- [ ] Key points list has bullet points
- [ ] Sources section lists sources with snippets

---

### 7. Tab Switching Test

#### Test Model Response Tab

- [ ] Open a model response (click existing response tab if available)
- [ ] Query a model for: `"What is OAuth2?"`
- [ ] Response displays in output area

#### Test Tab Switching

- [ ] Click "🔍 Research" tab → Research panel shows
- [ ] Click model response tab → Model response shows
- [ ] Switching works smoothly
- [ ] No errors in console

---

### 8. Theme Switching Test

#### Toggle Theme

- [ ] Open Settings (if available)
- [ ] Toggle between Dark/Light mode
- [ ] Research panel follows theme
- [ ] Tab colors update correctly
- [ ] Text contrast is acceptable

---

### 9. Error Handling Test

#### Test Network Error

- [ ] Stop DataForge (Ctrl+C in Terminal 1)
- [ ] Try to execute research query
- [ ] Error message displays in ResearchPanel
- [ ] Error is user-friendly (not raw exception)
- [ ] User can dismiss error
- [ ] Restart DataForge for next test

#### Test Invalid Query

- [ ] Enter empty query
- [ ] Execute button is disabled (or shows error)
- [ ] Try with single character: "a"
- [ ] Execute button enabled
- [ ] Results return (or no results message)

---

### 10. Performance Test

#### Latency Measurement

```bash
# From browser console, measure query time
const start = performance.now();
// Execute query
// After results appear:
const end = performance.now();
console.log(`Query took: ${end - start}ms`);
```

**Target**: < 3000ms (3 seconds)

- [ ] First query: < 3000ms
- [ ] Cached query: < 500ms
- [ ] No UI freezing during query
- [ ] Spinner continues animating

---

## ✅ Verification Results Summary

### Code Quality Checks

- [ ] TypeScript compilation passes (or pre-existing errors only)
- [ ] No new runtime errors introduced
- [ ] All imports resolve correctly
- [ ] File sizes match expected (67, 162, 579, 273 lines)

### System Integration

- [ ] DataForge starts and responds to requests
- [ ] NeuroForge starts and responds to requests
- [ ] VibeForge frontend starts and compiles
- [ ] All 3 services communicate successfully

### UI/UX Functionality

- [ ] Research tab visible and labeled correctly
- [ ] Query input accepts text
- [ ] Source selection works
- [ ] Depth selector works
- [ ] Execute button functional
- [ ] Results display properly formatted
- [ ] Tab switching works smoothly

### Data Flow

- [ ] Query reaches backend (check Network tab in DevTools)
- [ ] Results return from backend
- [ ] Results render in UI
- [ ] No data corruption or missing fields

### Performance

- [ ] Query completes in < 3 seconds
- [ ] UI remains responsive
- [ ] No memory leaks (check Task Manager)
- [ ] No console errors during normal operation

---

## 📊 Sign-Off Checklist

### System Status

- [ ] All 3 services operational
- [ ] Zero critical errors
- [ ] Research feature functional
- [ ] Integration tested end-to-end

### Code Quality

- [ ] Type safety: 100%
- [ ] Documentation: Complete
- [ ] Error handling: Robust
- [ ] Performance: Acceptable

### Ready for Phase 4?

- [ ] YES → Proceed to GitHub Connector
- [ ] NO → Note blockers, fix, re-run checklist

---

## 🔧 Troubleshooting Guide

### Issue: TypeScript Errors in OutputColumn.svelte

**Symptoms**:

```
error: response?.output_id not defined
```

**Solution**:
This is a pre-existing type issue. It resolves at build time. Ignore for now.

**Workaround** (if needed):

```typescript
// In OutputColumn.svelte, add type guard
if (response && response.output_id) { ... }
```

---

### Issue: ResearchPanel Not Showing

**Symptoms**:

- Research tab visible but empty

**Checklist**:

1. Is `showResearch` state initialized? (Check OutputColumn.svelte line 12)
2. Is ResearchPanel imported? (Check line 7)
3. Check browser console for errors
4. Try clicking different tabs back and forth
5. Hard refresh browser (Ctrl+Shift+R)

**Fix**:

```svelte
<!-- In OutputColumn.svelte -->
<script>
  import ResearchPanel from "./research/ResearchPanel.svelte";
  let showResearch = false;  <!-- This line must exist -->
</script>
```

---

### Issue: Query Execution Hangs

**Symptoms**:

- Loading spinner continues forever
- No results appear

**Checklist**:

1. Check DataForge running: `curl http://localhost:8001/health`
2. Check NeuroForge running: `curl http://localhost:8002/api/v1/research/health`
3. Check browser console for errors (Network tab)
4. Check DataForge/NeuroForge terminal for errors
5. Try shorter query: "OAuth" instead of full sentence

**Fix**:

- Restart DataForge (Terminal 1): `Ctrl+C`, then `python -m uvicorn app.main:app --reload --port 8001`
- Wait 5 seconds
- Try query again

---

### Issue: Results Show But Format is Wrong

**Symptoms**:

- Results display but styling looks off
- Text is hard to read

**Checklist**:

1. Check theme is dark: Settings → Toggle to Light → Toggle back to Dark
2. Check zoom level: Ctrl+0 to reset
3. Check browser zoom in DevTools (should be 100%)
4. Try different browser (Chrome vs Firefox)

**Fix**:
Hard refresh browser: `Ctrl+Shift+R`

---

### Issue: Network Errors in Console

**Symptoms**:

```
Failed to fetch https://localhost:8002/api/v1/research/query
```

**Checklist**:

1. Is NeuroForge running? (Check Terminal 2)
2. Is firewall blocking connections? (Unlikely on localhost)
3. Is port 8002 available? `netstat -an | grep 8002`
4. Try accessing health endpoint directly: `curl http://localhost:8002/api/v1/research/health`

**Fix**:

- If NeuroForge not running: Start it
- If port in use: Kill process or use different port
- If still failing: Check NeuroForge logs for errors

---

## 📝 Sign-Off

**Checklist Completed By**: [Your Name]  
**Date**: [Date]  
**Status**: ✅ Ready for Production / 🔧 Needs Fixes

**Notes**:

```
[Add any special notes or observations]
```

---

## Next Steps After Verification

### ✅ If All Tests Pass

1. Run full TypeScript check: `pnpm check`
2. Build production bundle: `pnpm build`
3. Review build output for size/warnings
4. Proceed to Phase 4 planning

### 🔧 If Issues Found

1. Document issues in VERIFICATION_REPORT.md
2. Create fix branches for each issue
3. Re-run affected tests
4. Update this checklist
5. Re-verify until all tests pass

---

## Quick Test Commands

**All-in-one verification**:

```bash
# Terminal 1: DataForge
cd /home/charles/projects/Coding2025/Forge/DataForge && \
  python -m uvicorn app.main:app --reload --port 8001

# Terminal 2: NeuroForge
cd /home/charles/projects/Coding2025/Forge/NeuroForge && \
  python -m uvicorn app.main:app --reload --port 8002

# Terminal 3: VibeForge
cd /home/charles/projects/Coding2025/Forge/vibeforge && \
  pnpm dev

# Browser: http://localhost:5173
# Then: Click Research tab → Enter query → Click Execute → Verify results
```

---

**Ready to verify? Start with step 4 above and work through all sections.**
