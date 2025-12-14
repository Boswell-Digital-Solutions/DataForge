# VibeForge_BDS – Phase 4 TODO (Production Integration & Enhancement)

**Status codes:** BACKLOG → READY → DOING → REVIEW → BLOCKED → DONE
**Priority:** P0 critical, P1 high, P2 normal, P3 nice-to-have

**Phase 4 Overview:**
Transform VibeForge_BDS from a polished prototype into a fully functional production application with real API integration, enhanced UX, optimized performance, and production-ready infrastructure.

**Focus Areas (6 tracks, 24 tasks):**
1. **Track A: Real API Integration** - Replace mocks with ForgeAgents BDS API (VF-400 to VF-403) - 4 tasks
2. **Track B: Enhanced UX & Accessibility** - Keyboard shortcuts, drag-drop, a11y (VF-410 to VF-413) - 4 tasks
3. **Track C: Performance Optimization** - Virtual scroll, lazy loading, caching (VF-420 to VF-423) - 4 tasks
4. **Track D: Advanced Admin Features** - Real-time monitoring, analytics, backups (VF-430 to VF-433) - 4 tasks
5. **Track E: Developer Experience** - Storybook, docs, playground (VF-440 to VF-443) - 4 tasks
6. **Track F: Production Hardening** - Rate limiting, monitoring, security (VF-450 to VF-453) - 4 tasks

**Recommended Execution Order:**
- **Sprint 1 (Week 1-2)**: Track A (VF-400 to VF-403) - Real API Integration (CRITICAL)
- **Sprint 2 (Week 3-4)**: Track F (VF-450 to VF-453) - Production Hardening (deploy readiness)
- **Sprint 3 (Week 5-6)**: Track C (VF-420 to VF-423) - Performance Optimization (scale)
- **Sprint 4 (Week 7-8)**: Track B (VF-410 to VF-413) - Enhanced UX (user delight)
- **Sprint 5 (Week 9-10)**: Track D (VF-430 to VF-433) - Advanced Admin (ops tools)
- **Sprint 6 (Week 11-12)**: Track E (VF-440 to VF-443) - Developer Experience (team velocity)

---

## Track A: Real API Integration (CRITICAL FOUNDATION)

### VF-400: ForgeAgents API Client Integration
**Status:** READY
**Priority:** P0
**Owner:** Claude
**Area:** API/Integration
**Files:** `src/lib/api/forgeAgentsClient.ts`, `src/lib/api/skillRegistry.ts`
**Deps:** Phase 3 Complete
**Estimated Time:** 6-8 hours

**Acceptance:**
- [ ] Update forgeAgentsClient to use real endpoints (http://localhost:8100/api/v1)
- [ ] Replace mock skillRegistry with real API calls to `/api/v1/bds/skills`
- [ ] Implement proper authentication flow with token refresh
- [ ] Add request/response logging for debugging
- [ ] Handle all API error scenarios (401, 403, 404, 429, 500, 503)
- [ ] Add retry logic with exponential backoff
- [ ] Test with real BDS skills (code_review, write_tests, generate_docs)
- [ ] Update all components consuming skillRegistry
- [ ] Write integration tests with real API (10+ scenarios)

**Implementation Details:**
- Remove mock data from skillRegistry.ts
- Use actual `/api/v1/bds/skills` endpoint
- Test authentication edge cases (expired token, invalid token)
- Handle rate limiting (429 responses with Retry-After header)
- Add request queue for rate limit compliance
- Update error messages to be user-friendly
- Add loading states during API calls
- Implement optimistic updates for better UX

**Success Criteria:**
- All 11 routes load real data from ForgeAgents API
- Skill Library shows actual BDS skills
- Testing Lab can invoke real skills and show outputs
- History shows real execution records
- Error handling gracefully manages all failure modes

---

### VF-401: Real Skill Invocation & Streaming
**Status:** BACKLOG
**Priority:** P0
**Owner:** Claude
**Area:** API/Execution
**Files:** `src/lib/api/forgeAgentsClient.ts`, `src/routes/testing/+page.svelte`
**Deps:** VF-400
**Estimated Time:** 5-6 hours

**Acceptance:**
- [ ] Implement skill invocation with real API POST `/api/v1/bds/skills/{id}/invoke`
- [ ] Add streaming support for real-time output (`?stream=true`)
- [ ] Display streaming tokens in Testing Lab
- [ ] Show execution metadata (tokens used, cost, latency, model)
- [ ] Handle streaming errors and interruptions
- [ ] Add abort functionality for long-running invocations
- [ ] Save execution results to history
- [ ] Test with all available BDS skills
- [ ] Add cost tracking and display

**Implementation Details:**
- Use Server-Sent Events (SSE) or WebSocket for streaming
- Parse incremental responses and update UI in real-time
- Show progress indicator with token count
- Implement cancel button to abort requests
- Calculate and display costs based on model pricing
- Store invocation results in localStorage + API
- Add export functionality (JSON, markdown)

**Success Criteria:**
- Users can invoke real BDS skills from Testing Lab
- Streaming output appears in real-time
- Execution metadata displayed accurately
- Cost tracking shows correct pricing
- Can abort long-running invocations

---

### VF-402: Live Skill Search & Filtering
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** API/Search
**Files:** `src/routes/library/+page.svelte`, `src/lib/api/forgeAgentsClient.ts`
**Deps:** VF-400
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Implement server-side search via `/api/v1/bds/skills/search?query={}`
- [ ] Add debounced search input (300ms delay)
- [ ] Filter skills by category, section, access level (client-side + API)
- [ ] Sort skills by name, usage count, rating (client + server)
- [ ] Add pagination for large skill lists (50 per page)
- [ ] Cache search results for 5 minutes
- [ ] Show search result count
- [ ] Add "Clear filters" button
- [ ] Test with 100+ skills

**Implementation Details:**
- Debounce search input to reduce API calls
- Use query params for filters (preserves state in URL)
- Implement infinite scroll or "Load More" button
- Cache results in memory with TTL
- Show skeleton loaders during search
- Highlight matching text in results
- Add keyboard navigation (arrow keys to navigate results)

**Success Criteria:**
- Search returns results in <200ms (with caching)
- Filters work correctly with API
- Pagination handles 100+ skills smoothly
- URL preserves search state (shareable links)

---

### VF-403: Analytics & Metrics Integration
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** API/Analytics
**Files:** `src/routes/analytics/+page.svelte`, `src/lib/api/forgeAgentsClient.ts`
**Deps:** VF-400
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Fetch real analytics from `/api/v1/bds/analytics`
- [ ] Display actual invocation counts, success rates, costs
- [ ] Show real-time metrics (last 24h, 7d, 30d, all time)
- [ ] Implement chart data from API responses
- [ ] Add date range selector
- [ ] Export analytics to CSV
- [ ] Show top skills by usage
- [ ] Display model usage breakdown
- [ ] Add cost trends over time

**Implementation Details:**
- Create analytics API endpoints if not exist
- Use Chart.js for data visualization
- Cache analytics data (5 min TTL)
- Add loading skeletons for charts
- Implement CSV export with proper formatting
- Show empty state if no data
- Add refresh button for latest metrics

**Success Criteria:**
- Analytics page shows real BDS usage data
- Charts render correctly with actual metrics
- Date range filtering works
- CSV export includes all relevant data
- Refresh updates metrics in real-time

---

## Track B: Enhanced UX & Accessibility

### VF-410: Command Palette (Cmd+K)
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** UX/Navigation
**Files:** `src/lib/components/CommandPalette.svelte`, `src/routes/+layout.svelte`
**Deps:** VF-400
**Estimated Time:** 5-6 hours

**Acceptance:**
- [ ] Create CommandPalette component with fuzzy search
- [ ] Trigger with Cmd+K (Mac) or Ctrl+K (Windows/Linux)
- [ ] Search across all routes, skills, workflows, history
- [ ] Show recent items at top
- [ ] Add keyboard navigation (arrow keys, Enter, Esc)
- [ ] Support actions (New Workflow, Run Skill, etc.)
- [ ] Add icons for each item type
- [ ] Highlight matching text
- [ ] Track usage analytics

**Implementation Details:**
- Use Fuse.js for fuzzy search
- Listen for keyboard shortcuts globally
- Index all searchable content on mount
- Show most recently accessed items first
- Support quick actions (e.g., "/workflow" to create workflow)
- Close on Esc or click outside
- Add keyboard shortcuts help (? key)
- Persist recent searches

**Success Criteria:**
- Cmd+K opens palette instantly (<50ms)
- Search returns results in <100ms
- Keyboard navigation feels smooth
- Can navigate entire app without mouse

---

### VF-411: Drag-and-Drop Workflow Builder
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** UX/Workflows
**Files:** `src/routes/workflows/+page.svelte`, `src/lib/components/DragDropWorkflow.svelte`
**Deps:** VF-400
**Estimated Time:** 6-7 hours

**Acceptance:**
- [ ] Implement drag-and-drop from Skill Library to Workflow builder
- [ ] Reorder steps by dragging within workflow
- [ ] Add visual feedback (drag ghost, drop zones)
- [ ] Support keyboard alternative (Tab, Shift+Tab, Space)
- [ ] Auto-save workflow on changes
- [ ] Undo/redo support (Cmd+Z, Cmd+Shift+Z)
- [ ] Show validation errors (missing inputs, circular dependencies)
- [ ] Add step configuration modal
- [ ] Test with touch devices

**Implementation Details:**
- Use @dnd-kit/core for drag-and-drop
- Show drop zones with visual indicators
- Validate workflow after each change
- Implement undo/redo stack (max 20 actions)
- Add touch event handlers for mobile
- Show preview of skill during drag
- Highlight invalid drop targets

**Success Criteria:**
- Drag-and-drop feels smooth (60fps)
- Can build complex workflows quickly
- Undo/redo works correctly
- Keyboard shortcuts work for accessibility
- Touch devices supported

---

### VF-412: Advanced Filtering & Search
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** UX/Search
**Files:** `src/lib/components/AdvancedSearch.svelte`
**Deps:** VF-402
**Estimated Time:** 3-4 hours

**Acceptance:**
- [ ] Add multi-select filters (categories, tags, access levels)
- [ ] Implement date range picker for history
- [ ] Add saved search presets
- [ ] Support complex queries (AND, OR, NOT operators)
- [ ] Show filter chips with counts
- [ ] Add "Clear all" button
- [ ] Persist filters in URL
- [ ] Add search suggestions/autocomplete
- [ ] Show result counts per filter

**Implementation Details:**
- Use Svelte stores for filter state
- Sync filters with URL query params
- Save presets to localStorage
- Implement query parser for complex searches
- Show active filters as removable chips
- Add keyboard shortcuts (Cmd+F for search)
- Highlight matching text in results

**Success Criteria:**
- Filters work across all list views
- URL preserves complete search state
- Saved presets persist across sessions
- Complex queries parse correctly

---

### VF-413: ARIA Compliance & Screen Reader Support
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Accessibility
**Files:** All components, `src/lib/utils/a11y.ts`
**Deps:** VF-410
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Audit all components for ARIA compliance
- [ ] Add proper ARIA labels, roles, descriptions
- [ ] Ensure keyboard navigation works everywhere
- [ ] Add skip links ("Skip to main content")
- [ ] Test with screen readers (NVDA, JAWS, VoiceOver)
- [ ] Ensure color contrast meets WCAG AA (4.5:1)
- [ ] Add focus indicators (visible outlines)
- [ ] Support reduced motion preference
- [ ] Add landmark regions

**Implementation Details:**
- Run axe-core automated accessibility tests
- Add ARIA labels to all interactive elements
- Implement focus trap for modals
- Add aria-live regions for dynamic content
- Test with keyboard only (no mouse)
- Ensure all images have alt text
- Add focus-visible for keyboard-only focus
- Respect prefers-reduced-motion media query

**Success Criteria:**
- 0 critical accessibility issues (axe-core)
- Can navigate entire app with keyboard only
- Screen readers announce content correctly
- Passes WCAG 2.1 AA compliance

---

## Track C: Performance Optimization

### VF-420: Virtual Scrolling for Large Lists
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Performance
**Files:** `src/lib/components/VirtualList.svelte`, list pages
**Deps:** VF-402
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Implement virtual scrolling for Skill Library (100+ items)
- [ ] Add virtual scrolling to History page (1000+ runs)
- [ ] Optimize rendering to show only visible items
- [ ] Smooth scrolling with <16ms frame time
- [ ] Handle dynamic item heights
- [ ] Add scroll restoration (remember position)
- [ ] Test with 10,000+ items
- [ ] Measure improvement (before/after metrics)

**Implementation Details:**
- Use svelte-virtual-list or custom implementation
- Render only visible items + buffer (5 above/below)
- Calculate scroll position based on average item height
- Update visible range on scroll (throttled)
- Implement intersection observer for performance
- Add scroll position persistence (localStorage)
- Test with different screen sizes

**Success Criteria:**
- Lists with 1000+ items render smoothly
- Initial render <100ms
- Scroll at 60fps consistently
- Memory usage stays constant (no leaks)

---

### VF-421: Code Splitting & Lazy Loading
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Performance
**Files:** `src/routes/`, Vite config
**Deps:** None
**Estimated Time:** 3-4 hours

**Acceptance:**
- [ ] Split routes into separate chunks
- [ ] Lazy load heavy components (charts, editors)
- [ ] Preload critical routes on hover
- [ ] Implement route-based code splitting
- [ ] Reduce initial bundle size by 50%
- [ ] Add loading indicators for lazy components
- [ ] Optimize Vite build config
- [ ] Analyze bundle with rollup-plugin-visualizer

**Implementation Details:**
- Use dynamic imports for routes
- Lazy load Chart.js only on Analytics page
- Preload components on link hover (prefetch)
- Split vendor chunks (React, lodash, etc.)
- Use Vite's manualChunks for optimal splitting
- Add Suspense boundaries with loading spinners
- Generate source maps for debugging

**Success Criteria:**
- Initial bundle <200KB (gzipped)
- Time to Interactive <2s on 3G
- Lighthouse performance score >90
- Each route loads independently

---

### VF-422: Caching Strategy & Optimization
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Performance
**Files:** `src/lib/utils/cache.ts`, Service Worker
**Deps:** VF-400
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Implement in-memory LRU cache for API responses
- [ ] Add service worker for offline caching
- [ ] Cache static assets (fonts, images, CSS)
- [ ] Cache skills list for 5 minutes
- [ ] Implement cache invalidation strategy
- [ ] Add cache-busting for new deployments
- [ ] Show stale data with refresh indicator
- [ ] Test offline functionality

**Implementation Details:**
- Create LRU cache utility (max 100 entries)
- Use Workbox for service worker generation
- Cache API responses with TTL (5-60 min)
- Implement stale-while-revalidate for skills
- Add cache version for invalidation
- Show "Update available" banner for new versions
- Persist cache to IndexedDB for offline

**Success Criteria:**
- Repeat visits load instantly (<100ms)
- App works offline (cached content)
- Cache invalidates correctly on updates
- No stale data shown after 5 minutes

---

### VF-423: Bundle Size & Asset Optimization
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Performance
**Files:** Vite config, images, fonts
**Deps:** VF-421
**Estimated Time:** 2-3 hours

**Acceptance:**
- [ ] Optimize images (WebP format, responsive sizes)
- [ ] Subset fonts (only used glyphs)
- [ ] Remove unused CSS (PurgeCSS)
- [ ] Minify SVG assets
- [ ] Compress API responses (gzip/brotli)
- [ ] Analyze and remove duplicate dependencies
- [ ] Add tree-shaking for libraries
- [ ] Measure bundle size in CI

**Implementation Details:**
- Use vite-imagetools for image optimization
- Subset Google Fonts with unicode-range
- Configure Tailwind to purge unused styles
- Use SVGO for SVG optimization
- Enable gzip/brotli compression in server
- Run dependency-cruiser to find duplicates
- Add bundlesize to CI pipeline

**Success Criteria:**
- Total bundle size <500KB (gzipped)
- Images optimized (50%+ size reduction)
- Fonts subset (only Latin characters)
- Zero duplicate dependencies

---

## Track D: Advanced Admin Features

### VF-430: Real-Time System Monitoring Dashboard
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Admin/Monitoring
**Files:** `src/routes/admin/+page.svelte`, monitoring components
**Deps:** VF-400
**Estimated Time:** 5-6 hours

**Acceptance:**
- [ ] Display real-time system health metrics
- [ ] Show API response times (p50, p95, p99)
- [ ] Display active users and sessions
- [ ] Show error rates and alerts
- [ ] Add CPU, memory, disk usage charts
- [ ] Implement auto-refresh (every 30 seconds)
- [ ] Add alerting for critical metrics
- [ ] Show service status (up/down)
- [ ] Add historical trends (24h, 7d)

**Implementation Details:**
- Fetch metrics from `/api/v1/admin/metrics`
- Use WebSocket for real-time updates
- Display charts with Chart.js
- Show color-coded status indicators
- Add alert thresholds (response time >1s)
- Implement email/Slack notifications
- Store historical data for trends

**Success Criteria:**
- Metrics update in real-time (<5s delay)
- Charts show accurate data
- Alerts trigger correctly
- Dashboard loads in <2s

---

### VF-431: User Activity Analytics
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Admin/Analytics
**Files:** `src/routes/admin/+page.svelte`, analytics components
**Deps:** VF-430
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Track user activity (logins, skill invocations)
- [ ] Show user session history
- [ ] Display most active users
- [ ] Show skill usage by user
- [ ] Add cohort analysis (daily/weekly/monthly active)
- [ ] Implement retention metrics
- [ ] Add user journey tracking
- [ ] Export analytics to CSV
- [ ] Add date range filtering

**Implementation Details:**
- Create activity tracking events
- Store events in database
- Aggregate metrics daily
- Calculate DAU/WAU/MAU
- Show funnel visualization
- Track conversion rates
- Add user segmentation

**Success Criteria:**
- Accurate user activity tracking
- Retention metrics calculated correctly
- Can export full user activity log
- Charts render performance data clearly

---

### VF-432: Automated Backup & Restore
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Admin/Operations
**Files:** Admin backup components, backup service
**Deps:** VF-430
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Implement full database backup
- [ ] Schedule automatic daily backups
- [ ] Add manual backup trigger
- [ ] Implement restore from backup
- [ ] Show backup history (last 30 days)
- [ ] Add backup verification
- [ ] Implement backup encryption
- [ ] Add S3/cloud storage integration
- [ ] Test restore process

**Implementation Details:**
- Create backup API endpoints
- Use pg_dump for PostgreSQL backups
- Schedule backups with cron
- Encrypt backups with AES-256
- Upload to S3 with versioning
- Add restore wizard UI
- Verify backup integrity
- Test disaster recovery

**Success Criteria:**
- Daily backups run automatically
- Backups encrypted and stored securely
- Restore process tested successfully
- Backup history visible in admin

---

### VF-433: Feature Flags System
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** Admin/Configuration
**Files:** `src/lib/stores/featureFlags.svelte.ts`, admin UI
**Deps:** VF-430
**Estimated Time:** 3-4 hours

**Acceptance:**
- [ ] Create feature flags store
- [ ] Add admin UI to toggle flags
- [ ] Implement flag checks in components
- [ ] Support user-level flags
- [ ] Add rollout percentage (gradual rollout)
- [ ] Persist flags in database
- [ ] Add flag expiration dates
- [ ] Log flag changes (audit trail)
- [ ] Test flag toggling

**Implementation Details:**
- Create FeatureFlags table in database
- Store flags in Svelte store (reactive)
- Wrap features with flag checks
- Implement rollout logic (% of users)
- Add flag management UI in admin
- Track flag usage analytics
- Add flag expiration dates

**Success Criteria:**
- Can toggle features without deployment
- Flags work for specific users
- Gradual rollout works correctly
- Audit trail shows all changes

---

## Track E: Developer Experience

### VF-440: Storybook Component Library
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** DevEx/Documentation
**Files:** `.storybook/`, `src/lib/components/*.stories.svelte`
**Deps:** None
**Estimated Time:** 5-6 hours

**Acceptance:**
- [ ] Set up Storybook 7 for Svelte 5
- [ ] Create stories for all 15 components
- [ ] Add controls for all component props
- [ ] Document component usage and examples
- [ ] Add accessibility addon
- [ ] Add responsive viewport addon
- [ ] Deploy Storybook to Netlify/Vercel
- [ ] Add MDX documentation
- [ ] Test in isolation

**Implementation Details:**
- Install @storybook/svelte
- Create .storybook/main.js config
- Write stories for each component
- Add JSDoc comments with examples
- Configure addons (a11y, viewport, docs)
- Add Storybook build to CI
- Deploy to storybook-vibeforge.netlify.app

**Success Criteria:**
- All components documented in Storybook
- Stories cover all prop variations
- Storybook deployed and accessible
- Team uses Storybook for development

---

### VF-441: Interactive API Documentation
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** DevEx/Documentation
**Files:** `docs/API_DOCS.md`, Swagger/OpenAPI spec
**Deps:** VF-400
**Estimated Time:** 3-4 hours

**Acceptance:**
- [ ] Generate OpenAPI/Swagger spec from API
- [ ] Create interactive API docs (Swagger UI)
- [ ] Document all API endpoints
- [ ] Add request/response examples
- [ ] Include authentication flow
- [ ] Add error code documentation
- [ ] Deploy docs to /api/docs
- [ ] Add "Try it out" functionality
- [ ] Keep docs in sync with API changes

**Implementation Details:**
- Use swagger-jsdoc to generate spec
- Add JSDoc comments to API routes
- Deploy Swagger UI at /api/docs
- Add authentication to Swagger UI
- Include example requests/responses
- Document error codes and messages
- Add API versioning documentation

**Success Criteria:**
- All endpoints documented
- Interactive testing works
- Docs stay in sync with API
- Developers can test API easily

---

### VF-442: Developer Onboarding Guide
**Status:** BACKLOG
**Priority:** P2
**Owner:** Claude
**Area:** DevEx/Documentation
**Files:** `docs/ONBOARDING.md`, video tutorials
**Deps:** VF-440
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Write comprehensive onboarding guide
- [ ] Document development setup
- [ ] Add architecture overview diagram
- [ ] Create coding standards guide
- [ ] Document testing strategy
- [ ] Add contribution guidelines
- [ ] Create video walkthrough (15-20 min)
- [ ] Add FAQ section
- [ ] Document common pitfalls

**Implementation Details:**
- Create ONBOARDING.md with steps
- Add setup instructions (pnpm install, etc.)
- Document folder structure
- Create architecture diagrams (Excalidraw)
- Document naming conventions
- Add PR template and review checklist
- Record screen capture tutorial
- Add troubleshooting section

**Success Criteria:**
- New developer can set up in <30 min
- All common questions answered
- Video tutorial covers key concepts
- Team follows coding standards

---

### VF-443: Component Playground & Sandbox
**Status:** BACKLOG
**Priority:** P3
**Owner:** Claude
**Area:** DevEx/Tools
**Files:** `src/routes/playground/+page.svelte`
**Deps:** VF-440
**Estimated Time:** 3-4 hours

**Acceptance:**
- [ ] Create interactive component playground
- [ ] Add live code editor (Monaco)
- [ ] Show live preview of components
- [ ] Support all component props
- [ ] Add preset examples
- [ ] Allow saving/sharing playgrounds
- [ ] Add export to CodeSandbox
- [ ] Support TypeScript
- [ ] Add hot reload

**Implementation Details:**
- Use Monaco Editor for code editing
- Live compile Svelte components
- Show preview in iframe
- Save playgrounds to localStorage
- Generate shareable URLs
- Add example library
- Support importing components

**Success Criteria:**
- Can edit and preview components live
- Code changes update instantly
- Can share playground links
- Useful for prototyping

---

## Track F: Production Hardening

### VF-450: Rate Limiting & Quota Management
**Status:** BACKLOG
**Priority:** P0
**Owner:** Claude
**Area:** Production/Security
**Files:** API middleware, quota stores
**Deps:** VF-400
**Estimated Time:** 5-6 hours

**Acceptance:**
- [ ] Implement rate limiting (100 req/min per user)
- [ ] Add quota tracking (1000 invocations/month)
- [ ] Show quota usage in UI
- [ ] Block requests when quota exceeded
- [ ] Add upgrade prompt for quota limit
- [ ] Implement token bucket algorithm
- [ ] Add admin override for limits
- [ ] Log rate limit violations
- [ ] Test edge cases

**Implementation Details:**
- Use Redis for rate limiting counters
- Implement sliding window algorithm
- Track quotas in PostgreSQL
- Show quota bar in header
- Display "X remaining" messages
- Add 429 response handling
- Implement backoff strategy
- Send email alerts at 80% quota

**Success Criteria:**
- Rate limiting works correctly
- Quota tracking is accurate
- Users notified before hitting limits
- Admin can adjust limits per user

---

### VF-451: Error Tracking & Monitoring (Sentry)
**Status:** BACKLOG
**Priority:** P0
**Owner:** Claude
**Area:** Production/Monitoring
**Files:** Sentry config, error handlers
**Deps:** VF-400
**Estimated Time:** 4-5 hours

**Acceptance:**
- [ ] Integrate Sentry for error tracking
- [ ] Capture frontend errors automatically
- [ ] Capture backend errors from API
- [ ] Add user context to errors
- [ ] Set up error alerting (email/Slack)
- [ ] Add source maps for debugging
- [ ] Configure error sampling (10%)
- [ ] Add custom error tags
- [ ] Test error reporting

**Implementation Details:**
- Install @sentry/svelte
- Add Sentry.init() to +layout
- Configure source map upload
- Add user ID and email to context
- Set environment tags (prod/staging)
- Configure alert rules
- Add performance monitoring
- Create error dashboard

**Success Criteria:**
- All errors captured automatically
- Alerts sent for critical errors
- Source maps work for debugging
- Error trends visible in Sentry

---

### VF-452: Performance Monitoring (Web Vitals)
**Status:** BACKLOG
**Priority:** P1
**Owner:** Claude
**Area:** Production/Monitoring
**Files:** Web Vitals tracking, performance store
**Deps:** VF-451
**Estimated Time:** 3-4 hours

**Acceptance:**
- [ ] Track Core Web Vitals (LCP, FID, CLS)
- [ ] Monitor Time to Interactive (TTI)
- [ ] Track API response times
- [ ] Add performance budget alerts
- [ ] Show metrics in admin dashboard
- [ ] Log performance data to analytics
- [ ] Add user timing marks
- [ ] Test on real devices
- [ ] Set up alerts for regressions

**Implementation Details:**
- Use web-vitals library
- Send metrics to analytics service
- Create performance dashboard
- Set thresholds (LCP <2.5s, FID <100ms)
- Add custom timing marks
- Track by route and device
- Monitor over time (trends)

**Success Criteria:**
- All Web Vitals tracked accurately
- Performance dashboard shows metrics
- Alerts trigger on regressions
- Can compare performance over time

---

### VF-453: Security Audit & Penetration Testing
**Status:** BACKLOG
**Priority:** P0
**Owner:** Claude
**Area:** Production/Security
**Files:** Security docs, penetration test report
**Deps:** VF-450
**Estimated Time:** 6-8 hours

**Acceptance:**
- [ ] Run OWASP ZAP security scan
- [ ] Audit for XSS vulnerabilities
- [ ] Test for SQL injection
- [ ] Check CSRF protection
- [ ] Audit authentication flow
- [ ] Test authorization boundaries
- [ ] Check for sensitive data exposure
- [ ] Review Content Security Policy
- [ ] Document security findings
- [ ] Fix all critical issues

**Implementation Details:**
- Run automated security scans
- Manual penetration testing
- Review all API endpoints
- Check input validation
- Test JWT token handling
- Review CORS configuration
- Audit logging and monitoring
- Create security checklist

**Success Criteria:**
- 0 critical security issues
- All vulnerabilities documented
- Security best practices followed
- Passes OWASP Top 10 checks

---

## Phase 4 Summary

**Total tasks:** 24 (VF-400 through VF-453)
**Status:** Starting with Track A (Real API Integration)
**Estimated duration:** 12-16 weeks (96 hours total)

**Track Breakdown:**
- Track A (Real API Integration): 4 tasks (~20 hours) - CRITICAL PATH
- Track B (Enhanced UX): 4 tasks (~18 hours)
- Track C (Performance): 4 tasks (~14 hours)
- Track D (Advanced Admin): 4 tasks (~17 hours)
- Track E (Developer Experience): 4 tasks (~15 hours)
- Track F (Production Hardening): 4 tasks (~18 hours)

**Phase 4 Completion Criteria:**
- All API calls use real ForgeAgents endpoints
- Real skill invocation with streaming output
- Command palette and keyboard shortcuts
- Performance optimized (Lighthouse >90)
- Production monitoring and alerting
- Complete developer documentation
- Security audit passed
- Ready for production deployment
