# VibeForge_BDS Visual Layout Guide

**Visual Reference for UI Implementation**  
**Version:** 1.0  
**Status:** Ready for Development  

---

## 📐 Full Application Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  SIDEBAR             HEADER                                      │
│  260px               56px height, sticky top                      │
│  ┌───────┐  ┌────────────────────────────────────────────────┐  │
│  │  VF   │  │ Dashboard    [search] charles@bds.com | v1.0.0 │  │
│  │  BDS  │  │              120 Skills | SAS: ON ●            │  │
│  │       │  └────────────────────────────────────────────────┘  │
│  ├───────┤  ┌────────────────────────────────────────────────┐  │
│  │ 📊 D  │  │                                                │  │
│  │ 📚 S  │  │  ┌──────────────────┐  ┌──────────────────┐   │  │
│  │ 🧠 P  │  │  │ ⚙️ EXECUTION     │  │ ✓ EVALUATION     │   │  │
│  │ ⚙️ E  │  │  │ MOD-E           │  │ MOD-V           │   │  │
│  │ ✓  E  │  │  │                  │  │                  │   │  │
│  │ 🔗 C  │  │  │ Pending: 3       │  │ Success: 92%     │   │  │
│  │ 📋 L  │  │  │ Failed: 1        │  │ Last run: 2m ago │   │  │
│  │ ⚙️ B  │  │  └──────────────────┘  └──────────────────┘   │  │
│  │       │  │                                                │  │
│  ├───────┤  │  ┌──────────────────┐  ┌──────────────────┐   │  │
│  │charles│  │  │ 🧠 PLANNING      │  │ 🔗 COORDINATION  │   │  │
│  │@bds   │  │  │ MOD-P           │  │ MOD-C           │   │  │
│  │       │  │  │                  │  │                  │   │  │
│  │ 120   │  │  │ Tasks: 5         │  │ Linked: 7        │   │  │
│  │Skills │  │  │ In Progress: 2   │  │ Agents: 4        │   │  │
│  │       │  │  └──────────────────┘  └──────────────────┘   │  │
│  │SAS: ON│  │                                                │  │
│  │ ●     │  │  ┌──────────────────────────────────────────┐  │  │
│  │       │  │  │ 📈 METRICS & LOGS                        │  │  │
│  │       │  │  │ [Execution Trend Chart - 24h view]       │  │  │
│  │       │  │  └──────────────────────────────────────────┘  │  │
│  └───────┘  │                                                │  │
│             │ Boswell Digital Solutions LLC • Internal Build │  │
│             └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘

Color Legend:
  SIDEBAR:           #1B1E24 (midnight)
  HEADER:            #1B1E24 (midnight) + border #C19745 (brass)
  PANELS:            #2A2D33 (graphite) + border rgba(255,255,255,0.08)
  MODULE HEADER:     brass-transparent + border #C19745
  TEXT (primary):    #F5F6F7 (off-white)
  TEXT (secondary):  #8A8F99 (cool-gray)
  ACCENT:            #C19745 (brass)
```

---

## 🎛️ Sidebar Detail

```
Width: 260px
Background: #1B1E24 (midnight)
Border-right: 1px solid rgba(193, 151, 69, 0.15)

┌─────────────────────────────┐
│ VibeForge_BDS               │  ← Cinzel Light 18px, #C19745
│ [●] INTERNAL • BDS ENG      │  ← Pill: #2A2D33 bg, #C19745 text
├─────────────────────────────┤
│                             │
│ 📊 Dashboard                │  ← Active: bg brass-transparent
│ 📚 Skills Library           │     border-left brass, text brass
│ 🧠 Planning                 │
│ ⚙️ Execution                │  ← Inactive: text cool-gray
│ ✓ Evaluation                │
│ 🔗 Coordination             │
│ 📋 System Logs              │
│ ⚙️ BDS Settings             │
│                             │
├─────────────────────────────┤
│ charles@bds.com             │  ← 11px cool-gray
│ 120 Skills Active           │  ← 10px brass
│ [●] SAS: ON                 │  ← 10px success green
└─────────────────────────────┘

Font:   Inter 13px
Icons:  Lucide thin-line
Gap:    4px between items
```

---

## 📋 Header Detail

```
Height: 56px
Position: Sticky, top: 0, z-index: 100
Background: #1B1E24 (midnight)
Border-bottom: 1px solid rgba(193, 151, 69, 0.15)
Margin-left: 260px (account for sidebar)

┌────────────────────────────────────────────────────────────┐
│ VibeForge_BDS Dashboard    [search bar]   charles@bds  v1.0│
│                                           Agents: 120  SAS●│
└────────────────────────────────────────────────────────────┘

Left side:
  Title:  Cinzel Light, 16px, #C19745, letter-spacing 0.5px

Right side (flex gap-5):
  User:   Inter 12px, #8A8F99
  Badge:  #2A2D33 bg, #C19745 text, 11px uppercase
  SAS:    #49C883 dot + "SAS: ON" text, 12px
  Time:   JetBrains Mono 11px, #8A8F99

All vertically centered, padding 0 24px
```

---

## 🔲 Module Component (Planning / Execution / Evaluation / Coordination)

```
┌──────────────────────────────────────┐
│ ⚙️ MODULE NAME              MOD-ID  │  ← Module header: brass-transparent
├──────────────────────────────────────┤
│                                      │
│ Status: [●●●] 75% complete         │  ← 14px body text
│ Last Run: 2 minutes ago             │
│ Executions (24h): 147               │
│                                      │
│ [View Details ▶]                    │  ← Secondary button
│                                      │
└──────────────────────────────────────┘

Module Header:
  Background: rgba(193, 151, 69, 0.05)
  Border-bottom: 1px solid rgba(193, 151, 69, 0.15)
  Icon:         18px, #C19745
  Title:        13px semibold, #C19745, uppercase
  Module ID:    10px monospace, #8A8F99, right-aligned

Content:
  Padding: 16px
  Gap: 8px between items
  Background: #2A2D33
  Border: 1px solid rgba(193, 151, 69, 0.1)
```

---

## 📊 Skills Library Panel

```
┌──────────────────────────────────────────────────────┐
│ 📚 Skills Library                                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Total: 120 skills | Internal: 75 | Public: 45      │
│ [Search]                    [Filter ▼]              │
│                                                      │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Skill Name      Category    Status    Actions  │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ CodeReview      Execution   ✓ Active  [Edit]   │ │
│ │ DocAnalyze      Planning    ✓ Active  [Edit]   │ │
│ │ Refactor        Execution   ✓ Active  [Edit]   │ │
│ │ StyleGuard      Evaluation  ⚠ Pending [Edit]   │ │
│ │ Summarize       Execution   ✗ Disabled [Edit]  │ │
│ │                                                 │ │
│ └─────────────────────────────────────────────────┘ │
│                                                      │
│ [< Previous]  Page 1 of 12  [Next >]               │
│                                                      │
└──────────────────────────────────────────────────────┘

Table styling:
  Header:     brass-transparent bg, #C19745 text
  Rows:       Hover: brass-transparent (3% opacity)
  Border:     1px solid rgba(255,255,255,0.06)
  Font:       Inter 13px, monospace for status
  Cell pad:   12px
```

---

## 🎬 Status Indicator Examples

```
Success (Green #49C883):
┌─────────────────────────────────┐
│ ✓ SUCCESS | Last run: 2m ago    │ ← Green background 15% opacity
└─────────────────────────────────┘    Green border 30% opacity
                                        Green text 100%

Warning (Amber #E8A64D):
┌─────────────────────────────────┐
│ ⚠ PENDING | Retry in 5s         │ ← Amber background 15% opacity
└─────────────────────────────────┘    Amber border 30% opacity
                                        Amber text 100%

Error (Red #EF4444):
┌─────────────────────────────────┐
│ ✗ FAILED | Error: timeout       │ ← Red background 15% opacity
└─────────────────────────────────┘    Red border 30% opacity
                                        Red text 100%

Active (Brass #C19745):
┌─────────────────────────────────┐
│ ● ACTIVE | 120 skills running   │ ← Brass background 15% opacity
└─────────────────────────────────┘    Brass border 30% opacity
                                        Brass text 100%

Inline Badge:
[✓ ACTIVE]  [⚠ PENDING]  [✗ FAILED]
```

---

## 🔧 Input & Button Examples

```
INPUT FIELD:
┌────────────────────────────────────────────┐
│ Label (12px, uppercase, #8A8F99)           │
├────────────────────────────────────────────┤
│ Placeholder text (cool-gray)               │
└────────────────────────────────────────────┘
  Border: 1px solid rgba(255,255,255,0.12)
  Padding: 10px 12px
  Height: 40px
  Focus: Border brass, shadow 0 0 0 3px rgba(193,151,69,0.1)

PRIMARY BUTTON:
┌──────────────────┐
│ Click me         │  Background: #C19745
└──────────────────┘  Text: #1B1E24
                      Padding: 10px 16px
                      Hover: #D4A859 + shadow
                      Active: #B08840
                      Radius: 4px

SECONDARY BUTTON:
┌──────────────────┐
│ Secondary        │  Border: 1px solid #6A87A6
└──────────────────┘  Text: #6A87A6
                      Background: transparent
                      Hover: rgba(106,135,166,0.1)
                      Radius: 4px

TERTIARY BUTTON:
┌──────────────────┐
│ Tertiary         │  No border, no background
└──────────────────┘  Text: #8A8F99
                      Hover: #C19745
                      Radius: 4px
```

---

## 📈 Dashboard Metrics Card

```
┌─────────────────────────────────────────────────────┐
│ 📊 EXECUTION METRICS                        MOD-E   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Executions (24h)    Success Rate    Avg Duration  │
│  ┌──────────────┐    ┌──────────────┐ ┌──────────┐ │
│  │     147      │    │    92.3%     │ │  1.24s   │ │
│  │ executions   │    │ (+2.1% ↑)    │ │ (-8% ↓)  │ │
│  └──────────────┘    └──────────────┘ └──────────┘ │
│                                                     │
│  Artifacts Generated  Errors Caught  SAS Violations│
│  ┌──────────────┐    ┌──────────────┐ ┌──────────┐ │
│  │      43      │    │       5      │ │    0     │ │
│  │ artifacts    │    │ (logged)     │ │ (clean)  │ │
│  └──────────────┘    └──────────────┘ └──────────┘ │
│                                                     │
│ [View Details] [Export Report] [Settings]          │
│                                                     │
└─────────────────────────────────────────────────────┘

Card:
  Background: #2A2D33
  Border: 1px solid rgba(193, 151, 69, 0.1)
  Radius: 6px
  Padding: 16px

Metric Boxes:
  Each: 120px width, 80px height
  Background: rgba(193, 151, 69, 0.03)
  Border: 1px solid rgba(193, 151, 69, 0.08)
  Radius: 4px
  Number: 24px bold, #off-white
  Label: 11px cool-gray
  Change: 11px (green ↑ or red ↓)
```

---

## 🔐 SAS Compliance Panel

```
┌──────────────────────────────────────────────────────┐
│ 🛡️ SAS COMPLIANCE STATUS                    MOD-SAS  │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Overall Score: 96.2% [████████░] COMPLIANT         │
│                                                      │
│ Policy Violations: 3 (this month)                    │
│ ├─ CodeReview: skipped 2 runs ⚠                     │
│ ├─ StyleGuard: 1 policy failure                     │
│ └─ Refactor: all good ✓                             │
│                                                      │
│ Last Audit: 2024-12-08 14:32 UTC                    │
│ Next Audit: 2024-12-09 04:00 UTC                    │
│                                                      │
│ [View Full Report] [Run Audit Now]                  │
│                                                      │
└──────────────────────────────────────────────────────┘

Progress Bar:
  Height: 6px
  Background: rgba(255,255,255,0.08)
  Fill: Linear gradient brass → violet
  Border-radius: 3px

Compliance:
  96-100%: Success green
  75-95%:  Warning amber
  0-74%:   Error red
```

---

## 📋 System Logs View

```
┌──────────────────────────────────────────────────────┐
│ 📋 SYSTEM LOGS (Last 100)                            │
├──────────────────────────────────────────────────────┤
│                                                      │
│ [Filter: All] [Level: All] [Hours: 24]              │
│                                                      │
│ 14:32:15 [INFO]  Skill execution started: CodeReview│
│ 14:32:16 [INFO]  Retrieved 5 files for analysis     │
│ 14:32:18 [INFO]  Execution complete: CodeReview     │
│ 14:32:19 [SUCCESS] Artifacts generated: 5          │
│ 14:32:20 [INFO]  PAORT session created: xyz-123    │
│ 14:32:25 [INFO]  SAS evaluation running...          │
│ 14:32:31 [SUCCESS] SAS: 94% pass rate               │
│ 14:32:32 [INFO]  Artifact storage complete         │
│ 14:33:01 [INFO]  Skill execution: DocAnalyze       │
│ 14:33:02 [WARNING] Execution slow (3.2s, avg 1.1s) │
│ 14:33:15 [SUCCESS] DocAnalyze complete             │
│ 14:33:16 [INFO]  Total artifacts: 43 (24h)         │
│                                                      │
│ [← Older Logs]  [Newer Logs →]                      │
│                                                      │
└──────────────────────────────────────────────────────┘

Log styling:
  Background: #1B1E24
  Font: JetBrains Mono 11px
  Line height: 1.6
  Timestamp: #8A8F99
  [INFO]:    #6A87A6
  [SUCCESS]: #49C883
  [WARNING]: #E8A64D
  [ERROR]:   #EF4444
  Message:   #F5F6F7
```

---

## 🎨 Color Swatches (Reference)

```
Primary Background:
████ #1B1E24 (Midnight Slate) - Sidebar, main background

Panel Background:
████ #2A2D33 (Graphite Gray) - Cards, panels, containers

Accent Colors:
████ #C19745 (Forge Brass)     - Primary action, headings, accents
████ #6A87A6 (Steel Blue)      - Secondary action, links
████ #7B5FF1 (BDS Violet)      - Premium accent, special elements

Text Colors:
████ #F5F6F7 (Off-White)       - Primary text
████ #8A8F99 (Cool Gray)       - Secondary text
████ #555557 (Disabled Gray)   - Disabled states

Status Colors:
████ #49C883 (Success Green)   - Success, active, positive
████ #E8A64D (Warning Amber)   - Warnings, pending, caution
████ #EF4444 (Error Red)       - Errors, failures, critical

Borders & Overlays:
████ rgba(255,255,255,0.08)   - Subtle borders
████ rgba(193,151,69,0.15)     - Brass accent borders
████ rgba(193,151,69,0.05)     - Brass backgrounds, low opacity
```

---

## 🔤 Typography Hierarchy

```
Heading 1 (Page Title):
Cinzel Light • 32px • #C19745 • letter-spacing 0.5px
"Dashboard"

Heading 2 (Section):
Cinzel Light • 24px • #C19745 • letter-spacing 0.4px
"Execution Metrics"

Heading 3 (Subsection):
Cinzel Light • 18px • #C19745 • letter-spacing 0.3px
"Module Settings"

Body Text:
Inter Regular • 14px • #F5F6F7 • line-height 1.5
"This is body text that explains something important."

Body Small:
Inter Regular • 12px • #F5F6F7 • line-height 1.4
"Smaller body text for secondary information."

Labels & Captions:
Inter Regular • 11px • #8A8F99 • uppercase • letter-spacing 0.3px
"SKILL COUNT"

Code (Inline):
JetBrains Mono • 12px • #7B5FF1
const result = await skill.execute();

Code (Block):
JetBrains Mono • 13px • #F5F6F7 • line-height 1.6
[Multi-line code blocks with syntax highlighting]

Logs:
JetBrains Mono • 11px • #F5F6F7 • line-height 1.6
14:32:15 [INFO] Execution started
```

---

## ✅ Visual Checklist Before Launch

- [ ] All panels have subtle borders (1px rgba(255,255,255,0.08))
- [ ] Sidebar is 260px wide, fixed left
- [ ] Header is 56px height, sticky
- [ ] Brass accents (#C19745) used consistently
- [ ] All buttons have 4px border-radius (not rounded)
- [ ] Spacing is 12px default (not 16px)
- [ ] Fonts loaded: Cinzel, Inter, JetBrains Mono
- [ ] Dark mode only (no light toggle)
- [ ] Status indicators correct colors (green, amber, red)
- [ ] Tables have brass-transparent header backgrounds
- [ ] Module headers have brass bottom border
- [ ] Input focus has brass border + glow shadow
- [ ] Watermark in bottom-right (faint)
- [ ] BDS Edition badge in header
- [ ] Skill count in sidebar footer
- [ ] SAS indicator persistent in header
- [ ] Icons are thin-line (Lucide style)
- [ ] All text readable on dark background (contrast check)
- [ ] No rounded corners > 6px on panels
- [ ] Gap between elements is 12px (tight, professional)

---

**Print this guide, reference during development, verify against final product.**

**Status:** Ready for UI Implementation  
**Version:** 1.0  
**Built by:** Boswell Digital Solutions LLC
