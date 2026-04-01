---
id: SPR-006
title: "Phase 6 — Frontend"
type: how-to
status: ACTIVE
owner: architect
agents: [coder]
tags: [project-management, sprint, workflow, frontend, html, css, javascript, ui]
related: [SPR-005, PRJ-001, BLU-001, BLU-002]
created: 2026-04-01
updated: 2026-04-01
version: 1.0.0
---

> **BLUF:** Sprint 006 builds the dark botanical-themed frontend — a single-page app with a query input, answer rendering with inline citation highlights, and expandable source cards. Exit criterion: the user types a question, sees a loading state, receives a formatted answer with clickable citations and source cards, all styled with the dark botanical design system. **This sprint runs in parallel with SPR-005. Do NOT modify files in `backend/`.**

# Sprint 006: Phase 6 — Frontend

**Phase:** 6 — Frontend
**Target:** Scope-bounded (AI-agent pace)
**Agent(s):** Developer Agent B (Frontend)
**Dependencies:** SPR-005 API contract (endpoints defined in BLU-002 §5 — frontend can be built against the spec before backend is wired)
**Blueprints:** BLU-001 §4 (frontend structure), BLU-002 §5 (response schema)

---

## ⚠️ Parallel Execution Warning

> [!CAUTION]
> **This sprint runs in parallel with SPR-005 (API Controllers), executed by a different Developer Agent.**
> - You MUST NOT modify any files in `backend/`, `scripts/`, or `tests/`.
> - You MAY ONLY modify files in `frontend/` directory: `index.html`, `css/style.css`, `js/app.js`.
> - The API endpoints you code against: `POST /api/query`, `GET /api/herbs`, `GET /api/status`
> - Response schemas are defined in BLU-002 §5. Code against those specs even though the backend routes may not be live yet.

---

## ⚠️ Mandatory Compliance — Every Task

| Governance Doc | Sprint Requirement |
|:---------------|:-------------------|
| **GOV-001** | Referential integrity (§12.1). |
| **GOV-003** | Clean, commented JavaScript. No minification. Descriptive function names. |
| **GOV-005** | Branch per task. Commits: `feat(SPR-006): T-NNN description`. |
| **GOV-007** | Update task status as you work. |

---

## Design System — Dark Botanical Theme

The frontend must feel **premium, modern, and richly themed** — not generic or minimal. Follow these design guidelines:

### Color Palette
```css
--bg-primary:      #0a0f0d;     /* Deep forest black */
--bg-secondary:    #111a16;     /* Dark moss */
--bg-card:         #162119;     /* Card background */
--bg-input:        #1a2820;     /* Input field */
--accent-primary:  #4ade80;     /* Vibrant green (actions, links) */
--accent-secondary:#34d399;     /* Emerald (hover states) */
--accent-gold:     #fbbf24;     /* Warm gold (citations, highlights) */
--text-primary:    #e2e8f0;     /* Light gray for body text */
--text-secondary:  #94a3b8;     /* Muted gray for secondary text */
--text-heading:    #f1f5f9;     /* Near-white for headings */
--border:          #2d3f35;     /* Subtle border */
--shadow:          rgba(0,0,0,0.4);
```

### Typography
- Import Google Font: **Inter** (400, 500, 600, 700)
- Headings: Inter 600-700, `--text-heading`
- Body: Inter 400, `--text-primary`
- Monospace (citations): system monospace stack

### Effects
- Glassmorphism on cards: `backdrop-filter: blur(10px)`, semi-transparent backgrounds
- Subtle green glow on focus/active states: `box-shadow: 0 0 20px rgba(74, 222, 128, 0.15)`
- Smooth transitions: `transition: all 0.3s ease`
- Loading spinner/pulse animation during query

---

## Developer Agent Tasks

### T-001: Create `frontend/css/style.css` — Design System
- **Branch:** `feature/SPR-006-T001-design-system`
- **Dependencies:** None
- **Deliverable:**
  - `frontend/css/style.css` — complete CSS design system
  - Must include:
    - CSS custom properties (variables) for the full color palette above
    - Reset/normalize styles
    - Typography system (body, headings h1-h4, paragraph, code)
    - Layout: centered container, max-width 800px, responsive padding
    - Card component: `.card` with glassmorphism, border, shadow
    - Input styles: `.query-input` — large, dark, with green focus glow
    - Button styles: `.btn-primary` — green gradient, hover effect, active press
    - Source card styles: `.source-card` — collapsible, with source type badge
    - Citation badge styles: `.citation` — gold text, clickable
    - Loading state: `.loading` — pulse animation or spinner
    - Answer container: `.answer` — rendered markdown-like typography
    - Responsive: works on mobile (min-width 320px) and desktop
    - Micro-animations: hover effects, focus transitions, card reveals
  - No external CSS frameworks — pure vanilla CSS
- **Acceptance criteria:**
  - All CSS variables render correct colors
  - Cards have glassmorphism effect
  - Input has visible green glow on focus
  - Button has gradient and hover state
  - Loading animation is visible
  - Responsive down to 320px width
- **Status:** [ ] Not Started

---

### T-002: Create `frontend/index.html` — Page Structure
- **Branch:** `feature/SPR-006-T002-html-structure`
- **Dependencies:** T-001
- **Deliverable:**
  - `frontend/index.html` — single-page application
  - Structure:
    ```
    <header>        — App title, tagline, subtle botanical decoration
    <main>
      <section#query>    — Search input + submit button
      <section#loading>  — Loading state (hidden by default)
      <section#answer>   — Answer text with citation markers (hidden)
      <section#sources>  — Source cards grid (hidden)
      <section#herbs>    — Herb index sidebar or section (optional)
    </main>
    <footer>        — Credits, data sources note
    ```
  - SEO: proper `<title>`, `<meta description>`, semantic HTML5
  - Links to `css/style.css` and `js/app.js`
  - All interactive elements have unique IDs for testing
  - Placeholder content that shows the layout before JS loads
- **Acceptance criteria:**
  - Page loads with visible header, input, and footer
  - All sections have unique IDs
  - Semantic HTML structure
  - Links CSS and JS correctly (relative paths — served by FastAPI)
- **Status:** [ ] Not Started

---

### T-003: Create `frontend/js/app.js` — Application Logic
- **Branch:** `feature/SPR-006-T003-app-logic`
- **Dependencies:** T-001, T-002
- **Deliverable:**
  - `frontend/js/app.js` — vanilla JavaScript application
  - Functions:
    ```javascript
    async function submitQuery(question)
    // POST /api/query, return QueryResponse

    function renderAnswer(answer)
    // Parse answer text, highlight [N] citations with gold badges
    // Make citations clickable (scroll to corresponding source card)

    function renderSources(sources)
    // Create source cards from sources array
    // Each card shows: source_type badge, title, year, excerpt
    // Cards are collapsible (click to expand/collapse)

    function showLoading() / hideLoading()
    // Toggle loading state visibility

    function handleError(error)
    // Display user-friendly error message

    async function loadHerbs()
    // GET /api/herbs, populate herb list section
    // Optional: clicking an herb name pre-fills the query input

    async function checkStatus()
    // GET /api/status, show doc count in header or footer
    ```
  - Event listeners:
    - Submit button click → `submitQuery()`
    - Enter key in input → `submitQuery()`
    - Citation click → scroll to source card
    - Herb name click → pre-fill query (optional)
  - State management:
    - Disable submit button during query
    - Show/hide loading, answer, sources sections appropriately
    - Handle empty results gracefully
  - Error handling:
    - Network errors → user-friendly message
    - API errors (500) → show error detail
    - Empty answer → "No results found" message
  - On page load: call `checkStatus()` and `loadHerbs()`
- **Acceptance criteria:**
  - Typing a question and clicking submit shows loading, then answer + sources
  - Citations `[1]`, `[2]` in answer text are highlighted gold and clickable
  - Clicking a citation scrolls to the corresponding source card
  - Source cards show type badge, title, year, and excerpt
  - Loading state is visible between submit and response
  - Errors display a user-friendly message
  - Works without page reload (SPA behavior)
- **Status:** [ ] Not Started

---

### T-004: Polish and verify
- **Branch:** `feature/SPR-006-T004-polish`
- **Dependencies:** T-001, T-002, T-003
- **Deliverable:**
  - Final visual polish pass:
    - Verify glassmorphism renders correctly
    - Verify all hover states and transitions work
    - Verify mobile responsiveness (test at 375px and 768px)
    - Add subtle entry animations when answer/sources appear
    - Ensure no layout shifts during loading → answer transition
  - Add a favicon (simple leaf emoji or generate one)
  - Verify all console errors are resolved
  - Test with a mock response (hardcode a sample `QueryResponse` in JS temporarily to verify rendering, then remove it)
- **Acceptance criteria:**
  - No console errors
  - All animations smooth (no jank)
  - Mobile layout works
  - Page feels premium and polished — not a prototype
- **Status:** [ ] Not Started

---

## Sprint Checklist

| Task | Agent | Status | Branch | Audited |
|:-----|:------|:-------|:-------|:--------|
| T-001 Design system | Developer B | [ ] | `feature/SPR-006-T001-design-system` | [ ] |
| T-002 HTML structure | Developer B | [ ] | `feature/SPR-006-T002-html-structure` | [ ] |
| T-003 App logic | Developer B | [ ] | `feature/SPR-006-T003-app-logic` | [ ] |
| T-004 Polish | Developer B | [ ] | `feature/SPR-006-T004-polish` | [ ] |

---

## Blockers

| # | Blocker | Filed by | DEF/EVO ID | Status |
|:--|:--------|:---------|:-----------|:-------|
| — | None | — | — | — |

---

## Sprint Completion Criteria

- [ ] All 4 tasks pass their acceptance criteria
- [ ] Page renders with dark botanical theme
- [ ] Query → loading → answer → sources flow works end-to-end
- [ ] Citations are highlighted and clickable
- [ ] Source cards show metadata
- [ ] Responsive on mobile and desktop
- [ ] No console errors
- [ ] No files modified outside `frontend/`
- [ ] Design feels premium, not prototypal

---

## Audit Notes (Architect)

**Verdict:** PENDING
**Deploy approved:** NO — pending audit
