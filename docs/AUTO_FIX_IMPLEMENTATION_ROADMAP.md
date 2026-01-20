# Incuera Auto-Fix: Implementation Roadmap

This document maps the strategic analysis recommendations to **your existing Incuera implementation** and provides concrete, code-level steps.

---

## 1. What You Have Today

| Layer | Implementation | Location |
|-------|----------------|----------|
| **Observe** | rrweb recording → ingest → `events` (JSONB), `sessions` | `packages/sdk`, `backend/app/api/ingest.py`, `backend/app/models/event.py` |
| **Reproduce (replay only)** | rrweb-player in Playwright → video | `backend/app/services/video.py`, `backend/app/workers/tasks.py` |
| **Analyze** | Molmo 2 (OpenRouter) on video: summary, `interaction_heatmap`, `error_events`, `conversion_funnel`, `action_counts` | `backend/app/services/molmo_analyzer.py`, `backend/app/api/videos.py` |
| **Fix / Verify** | ❌ None | — |
| **DeepContext / state** | ❌ Only rrweb DOM + `session.url`, viewport. No Redux/state. | SDK is `<script>`-light; no app-state instrumentation |
| **Selector strategy** | ❌ rrweb uses `nodeId` in a mirror; no mapping to CSS/ARIA for live app | — |

**rrweb events you already store** (in `event_data`):

- `type: 2` → FullSnapshot (full DOM)
- `type: 3` → IncrementalSnapshot with `data.source`:
  - `source: 2` → MouseInteraction: `{ type: 0–10, id: nodeId, x, y }` (Click=2, etc.)
  - `source: 3` → Scroll: `{ id, x, y }`
  - `source: 5` → Input: `{ id, text }` (and similar)
- `session.url` = start URL for the session

**Molmo output you already have** (per session):

- `error_events`: `[{ timestamp_ms, type, description }]`
- `interaction_heatmap`: `{ clicks: [{ timestamp_ms, x, y, element? }], hovers, scrolls }`
- `session_summary`, `conversion_funnel`, `action_counts`

---

## 2. Recommendation → Implementation Mapping

### 2.1 Verification Paradox: “Visual Regression Test Generator”

**Recommendation:** The agent should *create* a new Playwright test that validates the fix, not only rely on existing CI.

**Gap:** You have no verification loop and no test generation.

**Implementation (build on what you have):**

1. **New model fields** (`backend/app/models/session.py`):
   - `suggested_fix` (JSONB): `{ description, file, patch_hunk?, diff? }`
   - `playwright_test_snippet` (Text): generated test code
   - `verification_status` (String): `pending|passed|failed|skipped`

2. **New service** `backend/app/services/playwright_test_generator.py`:
   - **Input:** `session_id` → load `session.url`, `error_events`, `interaction_heatmap`, and rrweb `events` (from `get_session_events` / `Event`).
   - **Logic:**
     - For the error’s `timestamp_ms`, find the closest FullSnapshot + following IncrementalSnapshot up to that time to get DOM at “bug moment.”
     - From `interaction_heatmap.clicks` and rrweb `MouseInteraction` (type=Click, id, x, y), build an ordered list of “actions to reproduce”: `[{ action: 'click'|'scroll'|'type', selector?, x?, y?, value? }]`.
     - Use an LLM (same OpenRouter stack as Molmo) with a prompt: “Given this list of actions, this error description, and this DOM snippet, generate a Playwright test that: (1) navigates to `session.url`, (2) performs these actions, (3) asserts the bug is fixed (e.g. no error state, element visible).”
   - **Output:** string for `playwright_test_snippet`.

3. **New API** `POST /api/sessions/{session_id}/generate-test`:
   - Calls the test generator, saves to `playwright_test_snippet`, returns it.
   - Optional: run it in a sandbox and set `verification_status` (see 2.3).

4. **Frontend** (`frontend/incuera-frontend/.../sessions/[sessionId]/page.tsx`):
   - In the “Error Events” card, add “Generate Playwright test” per error. Display `playwright_test_snippet` in a code block with copy button.

**Dependency:** Reproduction engine (2.2) to produce a robust “actions to reproduce” list; you can start with a Molmo-only version (clicks from `interaction_heatmap` + `session_summary`) and iterate.

---

### 2.2 Playwright “Inverse Rendering” / Reproduction on Live App

**Recommendation:** Use Playwright for *semantic re-enactment* on the real app, not only for filming rrweb replay. Handle DOM selectors (CSS-in-JS, Shadow DOM, ARIA).

**Gap:** Today Playwright only records the rrweb-player. You never drive the live app. You have `nodeId` from rrweb, not selectors.

**Implementation:**

1. **New service** `backend/app/services/reproduction_engine.py`:
   - **Input:** `session_id`, optional `error_timestamp_ms` (to stop at the bug).
   - **Load:** `session.url`, `Event` list (ordered by `sequence_number`).
   - **Parse rrweb into “reproduction actions”:**
     - Rebuild a minimal “DOM mirror” from FullSnapshot + IncrementalSnapshot (Mutation) up to each interaction. For each MouseInteraction (Click, DblClick, etc.):
       - Resolve `id` → node in mirror → tag, `id`, `class`, `data-*`, `aria-*`, `href`/`src`, `placeholder`, `name`, text (first N chars). Prefer: `[data-testid]` > `[id]` (if stable) > `role+name` > `placeholder`/`name` > `tag.class` (strip hashes) > `x,y` as last resort.
     - For Input: resolve `id` to the same node and add `fill(value)`.
     - For Scroll: `id` + `x,y` → `locator.scrollIntoViewIfNeeded()` or `mouse.wheel`.
   - **Selector strategy (your “Achilles’ heel”):**
     - Prefer **ARIA and `data-testid`**: if the node or a parent has `data-testid`, `aria-label`, `role`+accessible name, use those.
     - For **CSS-in-JS / dynamic classes**: do **not** rely on `class` unless it looks static (e.g. no `css-xxx`, `emotion-`, `_`+hash). Prefer `[data-*]`, `id` (if not `root`/obviously generated), tag + nth-child as fallback.
     - **Shadow DOM:** rrweb can record shadow content. When building the mirror, if `isShadow` / host is present, output a selector that goes through `>>` (e.g. `page.locator('x-selector >> .. >> slot')`). Start with “no shadow” and add when you hit it.
   - **Output:** list of `{ action, selector, options? }` e.g. `[{ "action": "goto", "url": "..." }, { "action": "click", "selector": "[data-testid='submit']" }, ...]`.

2. **Playwright runner (same or separate module):**
   - `reproduction_runner.py`: given actions, `session.url`, and (optional) `--stop-at-ms`, run Playwright against a **configurable base URL** (staging/production). For each action: `page.goto`, `locator.click`, `locator.fill`, `mouse.wheel`, etc. Optionally take a screenshot at the end or at `error_timestamp_ms`.
   - Return: `{ success, steps_done, screenshot_url?, error? }`.

3. **APIs:**
   - `GET /api/sessions/{session_id}/reproduction-script` → returns the actions list (and/or a `.spec.ts`-style script).
   - `POST /api/sessions/{session_id}/reproduce` (body: `{ base_url?: string }`) → runs the runner, returns result. Requires a worker or async task if you don’t want to block HTTP.

4. **Config** (`backend/app/config.py`):
   - `reproduction_base_url` (optional): default target for `reproduce` when `base_url` is not provided.
   - `reproduction_timeout_ms`.

**Practical order:** Implement “rrweb → actions” and “actions → Playwright” with a simple selector strategy (e.g. `x,y` + `tag` + `id`/`data-testid` only). Add ARIA and class-filtering in a second pass. Consider a partner/acquire (e.g. Percy/Applitools) later for visual diffing; your value is the *agentic loop*, not the selector stack on day one.

---

### 2.3 “Crawl–Walk–Run” GTM: Suggested Fix (PR) with Human Review

**Recommendation:** Start with “Automated Reproduction + Suggested Fix” (PR, manual review); fully autonomous later.

**Gap:** No fix suggestion, no PR or patch.

**Implementation:**

1. **New service** `backend/app/services/fix_suggester.py`:
   - **Input:** `session_id`, `error_index` (which of `error_events`), (optional) `patch_target`: `frontend` | `backend` | `auto`.
   - **Gather context:**
     - `session_summary`, `error_events[error_index]`, `interaction_heatmap`, `session.url`, and the “reproduction actions” from 2.2 (or a Molmo-only approximation).
     - If you add a “codebase context” later: relevant files (e.g. from `session.url` path or from a project-config list). For now, skip or use a placeholder.
   - **LLM prompt:** “Given: error (type, description, timestamp), user actions, and page URL, suggest a minimal code change. Prefer: null checks, fixing selectors, correcting state updates. If frontend: return `{ file, diff, description }`. If unknown: return `{ description, possible_locations }`.”
   - **Output:** `{ description, file?, diff?, possible_locations? }` → store in `session.suggested_fix` (or a new `suggested_fixes` JSONB array keyed by `error_index`).

2. **API:**
   - `POST /api/sessions/{session_id}/suggest-fix` (body: `{ error_index?: number }`) → runs fix suggester, writes to `suggested_fix`, returns it.

3. **Frontend:**
   - In the Error Events card, add “Suggest fix” next to “Generate Playwright test.” Show `suggested_fix.description` and `diff` in a code block; “Copy” and “Create PR” (the latter can be a link to pre-filled GitHub “new PR” or a webhook to your backend that uses GitHub API to create a draft PR from `diff`). No need for full autonomy; the copy button alone satisfies “suggested fix.”

4. **DB:**
   - `suggested_fix` JSONB on `Session` is enough for v1. If you want one fix per error: `suggested_fixes` JSONB `{ "0": {...}, "1": {...} }` or a separate `session_fix_suggestions` table.

**Later (enterprise “run”):** Add a “Create PR” action that uses GitHub/GitLab API with a bot token, and an optional “auto-merge after CI green” for customers who opt in.

---

### 2.4 Visual Regression Test as Part of Verification

**Recommendation:** Use a Playwright test that specifically asserts the “fixed” state (and optionally a baseline image).

**How it fits:** The “Visual Regression Test Generator” (2.1) already produces `playwright_test_snippet`. Extend that snippet to include:

- `expect(locator).toBeVisible()` or `expect(locator).toHaveText(...)` for the fixed state.
- Optional: `await expect(page).toHaveScreenshot('after-fix.png')` for visual regression. This requires a baseline in the repo; you can make it opt-in via project settings.

**Concrete change:** In `playwright_test_generator.py` prompt, add: “Include an assertion that the error is resolved (e.g. element is visible, no error message). Optionally add `toHaveScreenshot` if the project uses Playwright screenshots.”

---

### 2.5 DeepContext / App State (Optional, Heavier)

**Recommendation:** Map visual timestamps to app state (e.g. Redux) and backend calls for better root-cause and patches.

**Gap:** Your SDK is rrweb-only. No Redux/ Zustand/backend tracing.

**Options:**

- **A) Keep it light (recommended for now):** Don’t add DeepContext. Your differentiator is “reproduce from rrweb + video” and “suggested fix from description + actions.” You can still get far with `session_summary`, `error_events`, `interaction_heatmap`, and rrweb events.
- **B) Optional “state snapshot” in SDK:** In `packages/sdk/src/index.ts`, add an optional `getStateSnapshot?: () => Record<string,unknown>`. For example, in a Redux app, `getStateSnapshot: () => store.getState()`. On each `flush` or on a timer, append a rrweb `Custom` event with `{ type: 'state', data: getStateSnapshot() }`. Backend stores it; `fix_suggester` and `playwright_test_generator` can use “state at `error_timestamp_ms`” in the prompt. This stays opt-in and does not require DeepContext-level backend tracing.
- **C) Full DeepContext:** Frontend state + backend distributed tracing and correlation. New SDK surface, backend pipeline, and storage. Defer until you have design partners who need it.

**Suggested path:** Implement A for the roadmap; add B only if early users have Redux/Zustand and ask for it.

---

### 2.6 Nail Reproduction First (Validation Path)

**Recommendation:** Build “Automated Reproduction” first; prove >70% Playwright reproduction before promising Auto-Fix.

**How to do it with your stack:**

1. **Metric:** For each session with `error_events` and a valid `session.url`, run `reproduction_runner` (2.2) and record:
   - `reproduction_success`: did the script run without crashing?
   - `reproduction_match`: did you reach “the same” state? (Heuristic: same final URL + similar DOM? Or: screenshot similarity at `error_timestamp_ms`? Start simple: same URL + no Playwright exception.)
2. **Dashboard / internal tool:** A simple “Reproduction report” that, for the last N sessions with errors, shows `reproduction_success` and `reproduction_match` and a link to the reproduction script. No need to expose in the main UI at first.
3. **Iterate on selectors:** When `reproduction_success` is low, inspect failures: is it `id`/`data-testid` missing? Add ARIA. Is it CSS-in-JS? Strip `class` and use `nth-child` or `x,y` as fallback. When `reproduction_match` is low, tighten “same state” (e.g. add screenshot diff or DOM checksum at `error_timestamp_ms`).

**Priority:** Implement 2.2 (reproduction engine + runner) and this metric before investing heavily in 2.1 and 2.3. The analysis is right: if reproduction fails, the patch is worthless.

---

### 2.7 Pricing / GTM and Rebranding

**Recommendation:** “Agentic DevOps” / “automate the boring parts”; tier by “Auto-Fix attempts” and “Engineering Hours Saved.”

**Implementation (product, not code):**

- **Metering:** Add `auto_fix_attempts` (or `reproduction_runs` + `suggest_fix_calls`) to the usage you store per project. You can add a `project_usage` or `usage_events` table and increment on:
  - `POST /reproduce`
  - `POST /suggest-fix`
  - `POST /generate-test`
- **Plans:** Enforce limits in middleware or in each of these endpoints based on `project.plan` (Starter: 10, Growth: 50, etc.). You don’t yet have `project.plan`; add a `plan` column (or `subscription_tier`) and a `limits` JSONB `{ "auto_fix_attempts": 10 }` for flexibility.
- **Rebranding:** Copy and in-app strings: shift from “we replace engineers” to “reproduce in 3 minutes, review in 3 more, get back to building.” No code changes, but worth doing in the same release as “Suggested fix” and “Generate test.”

---

## 3. Suggested Build Order

| Phase | Deliverable | Dependencies |
|-------|-------------|--------------|
| **1** | `reproduction_engine.py`: rrweb events → list of Playwright actions (selector strategy v1: `data-testid`, `id`, `x,y`+tag) | `Event` model, `get_session_events` |
| **2** | `reproduction_runner.py` + `POST /reproduce` (or async job); `reproduction_success` / `reproduction_match` metric and internal report | Phase 1, `session.url`, Playwright in backend |
| **3** | `playwright_test_generator.py` + `POST /generate-test`, `playwright_test_snippet` on Session; “Generate Playwright test” in Error Events card | Phase 1, Molmo `error_events` + `interaction_heatmap` |
| **4** | `fix_suggester.py` + `POST /suggest-fix`, `suggested_fix` on Session; “Suggest fix” + copy in UI | Phase 1, `error_events`, `session_summary` |
| **5** | Optional: run generated test in sandbox and set `verification_status`; optional `toHaveScreenshot` in generator | Phase 2, 3 |
| **6** | `project.plan` / `limits`, metering on `/reproduce`, `/suggest-fix`, `/generate-test`; rebranding | — |

---

## 4. File and Schema Changes Checklist

**New files**

- `backend/app/services/reproduction_engine.py`
- `backend/app/services/reproduction_runner.py`
- `backend/app/services/playwright_test_generator.py`
- `backend/app/services/fix_suggester.py`

**New API routes** (e.g. under `backend/app/api/` or a new `auto_fix.py` router)

- `GET /api/sessions/{id}/reproduction-script`
- `POST /api/sessions/{id}/reproduce`
- `POST /api/sessions/{id}/generate-test`
- `POST /api/sessions/{id}/suggest-fix`

**DB migrations**

- `session.suggested_fix` JSONB nullable
- `session.playwright_test_snippet` TEXT nullable
- `session.verification_status` VARCHAR nullable
- (Optional) `session.reproduction_result` JSONB for last `reproduce` run
- (Optional) `project.plan` or `project.subscription_tier`, `project.usage_limits` JSONB

**Config** (`backend/app/config.py`)

- `reproduction_base_url`, `reproduction_timeout_ms`
- (Optional) `openrouter_fix_model`, `openrouter_test_model` if you use different models for fix vs test generation

**Frontend**

- Error Events card: “Generate Playwright test”, “Suggest fix”, display of `playwright_test_snippet` and `suggested_fix.diff` with copy.

---

## 5. rrweb Event Reference (for Reproduction Engine)

- **FullSnapshot:** `type: 2`, `data: { node: ... }`. Rebuild mirror from here.
- **IncrementalSnapshot**
  - `data.source === 2` (MouseInteraction): `{ type, id, x, y }`. `type`: 0=MouseUp, 1=MouseDown, 2=Click, 3=ContextMenu, 4=DblClick, 5=Focus, 6=Blur, 7–10=Touch*.
  - `data.source === 3` (Scroll): `{ id, x, y }`.
  - `data.source === 5` (Input): `{ id, text }` (or similar; check rrweb types for `<input>`/`<textarea>`).
- **Mirror:** `id` in these events refers to the `id` in the serialized DOM (in FullSnapshot and Mutation adds). You must replay FullSnapshot + Mutations in order to resolve `id` → `{ tagName, attributes, childIds }` and then derive selectors.

---

## 6. Open Points

- **Reproduction target:** Staging vs production (URL override, env). `reproduce` `base_url` is enough for v1.
- **Auth for reproduction:** If the app is behind login, you’ll need cookies or a token. Not in scope for first reproduction; start with public or publicly reachable staging.
- **Percy/Applitools:** Revisit when selector flakiness becomes the main limiter; your moat is the Observe → Reproduce → Fix → Verify loop, not the low-level selector strategy on day one.

---

*Summary: You already have Observe (rrweb + ingest) and Analyze (Molmo). The largest leverage is **Reproduce** (rrweb→Playwright actions, then run on live app) and **Verify** (Playwright test generator). Implement reproduction and its success metric first; then add suggested fix and test generation. Defer DeepContext; keep the SDK light. Add “Suggested fix” and “Generate test” in the UI with manual copy/Create PR to match the crawl–walk–run GTM.*
