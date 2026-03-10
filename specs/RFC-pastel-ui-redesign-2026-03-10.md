# RFC: Full UI Redesign — Pastel Product Edition

## Context

The NotebookLLM frontend (`src/frontend-web`) currently renders a **2-column grid** (340px left sidebar + fluid center) with a fixed **slide-over right panel** (430px). The center stage (`KnowledgeCanvas`) mixes a CSS-layered "canvas viewport" background with DOM-based source board cards, chat response, prompt composer, and pinned notes — creating a cluttered, cramped experience that buries the primary answer interaction.

**What is broken:**
- The center canvas tries to do too much: source cards, response, prompt, pinned notes, and a decorative viewport overlay all compete for attention.
- The left sidebar acts as both a source gallery and a preview panel, leading to scroll fatigue in narrow space.
- The studio slide-over is the only way to access chat settings, podcast, and insights — all hidden behind a toggle.
- Whitespace is insufficient; panels are nested 3-4 levels deep with tight paddings.
- `@react-three/fiber` and `three` are in `package.json` but effectively unused (the `CanvasViewport` is purely CSS).

**Hard constraints:**
1. All existing routes (`/auth/*`, `/notebooks`, `/notebooks/:id`, `/notebooks/:id/sources/:sourceId`) are unchanged.
2. All backend API contracts remain untouched.
3. All existing functionality must continue working (auth, CRUD, chat, citations, podcast, jobs, chunks).
4. Zustand stores (`useAuthStore`, `useWorkspaceStore`) remain the source of truth for domain state.
5. Tailwind 3 + CSS custom property token system stays.

---

## Critique — What Could Go Wrong

### Pitfalls
1. **"Just a UI change" underestimates scope.** The `WorkspacePage` is 608 lines orchestrating 20+ store selectors, 6 TanStack queries, and a job polling loop. Touching its JSX risks breaking wiring. Mitigation: refactor JSX composition only; leave business logic functions untouched.
2. **Three.js dead weight.** `@react-three/fiber`, `@react-three/drei`, and `three` add ~500KB to the bundle but do nothing. Removing them is clean but needs verification that no import references remain.
3. **Theme token explosion.** The 3 theme token sets in `globals.css` already define ~80+ properties each. Adding new tokens for the redesign (e.g. `--gallery-rail-width`, `--studio-width`) is manageable, but undisciplined growth makes maintenance painful.

### Edge Cases
4. **Mobile collapse.** Current layout does `xl:grid-cols-[340px_...]`. The redesign must ensure the center-first flow at <1024px doesn't lose access to source gallery or studio.
5. **Empty states.** New notebooks with 0 sources, new sessions with 0 messages, failed podcast jobs — all need explicit handling in the new layout.
6. **Streaming mid-resize.** If the studio panel is opened while a response is streaming, the center layout must not jump or re-mount the `ReactMarkdown` component.

### Dependencies Not Mentioned
7. **`lib/api.ts` (1025 lines)** defines all types and API functions. It is read-only for this redesign, but the type interfaces (`SourceDocument`, `ChatMessageRecord`, `Citation`, etc.) constrain component prop contracts.
8. **`use-workspace-queries.ts`** hooks wrap TanStack Query. They must remain the data-fetching layer.
9. **The existing `use-workspace-store.test.ts`** covers selection toggling and node position updates. New UI state slices need tests.

---

## Options

### Option A: Conservative — Restyle In-Place

**Approach:** Keep the existing component tree intact. Apply spacing, typography, and color changes through CSS token updates and Tailwind class modifications. Move the canvas header/footer elements into cleaner zones but don't restructure the component hierarchy.

| Dimension | Assessment |
|---|---|
| **Risk** | Low — no component tree changes |
| **Effort** | ~2-3 days |
| **Outcome** | Spacious feel but same cramped architectural bones survive. Studio stays as slide-over. Canvas still tries to do everything. |
| **Maintenance** | Same component complexity. Somewhat lipstick-on-a-pig. |

### Option B: Balanced — 2-Panel + Slide Studio Refactor ✅

**Approach:** Restructure into 3 clear zones with new components while preserving all business logic in `WorkspacePage`. The key changes:

1. **Shell**: New `AppShell` replaces `WorkspaceShell`. Left rail (source gallery) is a collapsible 300px column. Center is the dominant `AnswerBoard`. Right studio stays as slide-over but gets wider (480px) and tabbed content improvements.
2. **Answer Board**: New component replaces `KnowledgeCanvas`. One dominant answer card, linked sources ribbon, docked prompt composer, pinned insights rail. No canvas viewport overlay.
3. **Source Gallery**: Redesigned `SourceGallery` replaces `SourceNebula`. Larger cards, cleaner upload zone, stronger delete affordance.
4. **Studio**: Redesigned `StudioPanel` replaces `AIStudioPanel`. Cleaner tab UX, less widget noise, better podcast progress display.
5. **Remove Three.js deps**: Uninstall `three`, `@react-three/fiber`, `@react-three/drei`, delete `AmbientScene.tsx`, `KnowledgeNode.tsx`, `KnowledgeThread.tsx`.
6. **Motion system**: Replace `floatDrift` (infinite) with event-driven spring presets. Add `prefers-reduced-motion` alternate path for all Framer Motion animations.

| Dimension | Assessment |
|---|---|
| **Risk** | Medium — component tree restructure, but business logic stays in page |
| **Effort** | ~5-7 days |
| **Outcome** | Clean, spacious product shell. Answer-first experience. Studio as a power-user drawer. Premium feel. |
| **Maintenance** | Cleaner component boundaries. Easier to extend. |

### Option C: Cutting-Edge — Full Component Library Extraction

**Approach:** Extract all UI primitives into a dedicated design system package. Build a proper Storybook. Implement CSS Container Queries for responsive behavior instead of media queries. Use View Transitions API for page-level animation.

| Dimension | Assessment |
|---|---|
| **Risk** | High — new build tooling, Storybook setup, Container Queries have limited Tailwind 3 support |
| **Effort** | ~10-14 days |
| **Outcome** | Best long-term foundation but ships much later |
| **Maintenance** | Excellent — but over-engineered for current team size |

---

## Recommendation

**Option B: Balanced.**

It delivers the spacious, answer-first redesign the spec demands while staying within practical scope. The tradeoff accepted: we don't get a formal Storybook or Container Queries. The tradeoff avoided: we don't ship a restyled version of the same cramped architecture (Option A), and we don't burn two weeks on infrastructure (Option C).

---

## Data Flow

The data flow through the application is unchanged. What changes is the **component composition** within `WorkspacePage`:

```
┌─────────────────────────────────────────────────────────────┐
│                       TopChrome (unchanged logic)           │
│  notebook switcher · search · theme pills · profile/logout  │
├────────┬──────────────────────────────────┬─────────────────┤
│        │                                  │                 │
│ Source  │        Answer Board              │   Studio Panel  │
│ Gallery │  ┌─────────────────────────┐     │   (slide-over)  │
│ (left   │  │ Answer Card (dominant)  │     │   ┌───────────┐ │
│  rail)  │  │  - markdown response    │     │   │ Chat tab  │ │
│         │  │  - streaming indicator  │     │   │ Podcast   │ │
│ Upload  │  │  - citation cards       │     │   │ Insights  │ │
│ Zone    │  └─────────────────────────┘     │   └───────────┘ │
│         │  ┌─────────────────────────┐     │                 │
│ Source   │  │ Linked Sources Ribbon   │     │                 │
│ Cards   │  └─────────────────────────┘     │                 │
│         │  ┌─────────────────────────┐     │                 │
│         │  │ Prompt Composer (docked)│     │                 │
│         │  └─────────────────────────┘     │                 │
│         │  ┌─────────────────────────┐     │                 │
│         │  │ Pinned Insights Rail    │     │                 │
│         │  └─────────────────────────┘     │                 │
└────────┴──────────────────────────────────┴─────────────────┘
```

**State flow remains identical:**
```
WorkspacePage (orchestrator)
  ├─ useWorkspaceStore (Zustand) — all UI + domain state
  ├─ useAuthStore (Zustand) — auth session
  ├─ TanStack Query hooks — server data
  └─ props down to presentation components
```

No new stores are created. New state slices added to `useWorkspaceStore`:
- `uiShellState.galleryCollapsed: boolean` (left rail toggle)
- Theme persistence already exists and is preserved.

---

## Proposed Changes

### Layout Components

#### [MODIFY] [WorkspaceShell.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/layout/WorkspaceShell.tsx)
Replace 2-column grid with responsive 3-zone shell. Left rail becomes collapsible at a breakpoint. Center is fluid and dominant. Right stays as slide-over.

#### [MODIFY] [TopChrome.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/layout/TopChrome.tsx)
Simplify chrome: reduce vertical height, clean up button groups, ensure theme pills are always visible on desktop.

#### [MODIFY] [PanelShell.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/layout/PanelShell.tsx)
Update inner panel styling with increased border-radius, updated shadows, and comfortable padding.

---

### Center — Answer Board

#### [NEW] [AnswerBoard.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/answer/AnswerBoard.tsx)
Replaces `KnowledgeCanvas`. Composes: dominant answer card, linked sources ribbon, prompt composer, pinned insights rail. All existing props/callbacks are threaded from `WorkspacePage`.

#### [MODIFY] [AIResponsePanel.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/chat/AIResponsePanel.tsx)
Increased padding, larger typography, cleaner expand/collapse animation. Becomes the single dominant center element.

#### [MODIFY] [PromptComposer.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/chat/PromptComposer.tsx)
Dock at bottom of answer board. Slightly larger textarea, cleaner chip styling.

---

### Source Gallery (Left)

#### [MODIFY] [SourceNebula.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/sources/SourceNebula.tsx)
Rename to `SourceGallery`. Larger source cards, calmer colors, stronger delete affordance with confirm flow. Upload zone redesigned as "add to notebook" surface.

#### [MODIFY] [DocumentOrb.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/sources/DocumentOrb.tsx)
Rename to `SourceCard`. Larger, calmer design. Clear status badges. Explicit delete button with confirm.

#### [MODIFY] [UploadDropzone.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/sources/UploadDropzone.tsx)
Redesigned as clean "add to notebook" surface supporting file + URL ingest.

---

### Studio (Right)

#### [MODIFY] [AIStudioPanel.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/studio/AIStudioPanel.tsx)
Wider panel (480px). Cleaner tab styling. Chat settings with less widget noise. Podcast tab with prominent generation UX. Insights tab with summary-first cards.

#### [MODIFY] [PodcastStudio.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/studio/PodcastStudio.tsx)
Improved progress/waveform readability. Prominent generate button.

---

### Deletions — Three.js Dead Weight

#### [DELETE] [AmbientScene.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/canvas/AmbientScene.tsx)
#### [DELETE] [KnowledgeNode.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/canvas/KnowledgeNode.tsx)
#### [DELETE] [KnowledgeThread.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/canvas/KnowledgeThread.tsx)
#### [DELETE] [KnowledgeCanvas.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/canvas/KnowledgeCanvas.tsx)
#### [DELETE] [CanvasViewport.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/components/canvas/CanvasViewport.tsx)
#### [DELETE] shaders directory

Remove `three`, `@react-three/fiber`, `@react-three/drei` from `package.json`.

---

### Styles & Theme

#### [MODIFY] [globals.css](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/styles/globals.css)
- Add new spacing/layout tokens to all 3 theme sets.
- Remove canvas-specific tokens (`--canvas-*`) since the viewport is deleted.
- Add `--gallery-rail-width`, `--studio-panel-width`, `--answer-board-max-width` tokens.
- Increase default body/card padding scale.

#### [MODIFY] [tailwind.config.js](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/tailwind.config.js)
Add new box-shadow presets for the redesigned surfaces.

#### [MODIFY] [motion.ts](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/animations/motion.ts)
Replace infinite `floatDrift` with event-driven `openGallery`, `sendPrompt`, `answerAppear` variants. All use spring transitions. No infinite animations.

---

### Pages

#### [MODIFY] [WorkspacePage.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/pages/WorkspacePage.tsx)
Replace `KnowledgeCanvas`, `SourceNebula`, `AIStudioPanel` composition with `AnswerBoard`, `SourceGallery`, `StudioPanel`. All business logic (handlers, effects, memos) stays untouched.

#### [MODIFY] [NotebooksPage.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/pages/NotebooksPage.tsx)
Update card styles and spacing for consistency with the new visual system.

#### [MODIFY] [LoginPage.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/pages/LoginPage.tsx)
Update spacing, typography, and panel styling.

#### [MODIFY] [RegisterPage.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/pages/RegisterPage.tsx)
Update spacing, typography, and panel styling.

#### [MODIFY] [SourceDetailPage.tsx](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/pages/SourceDetailPage.tsx)
Update chunk inspector styles for consistency.

---

### Store

#### [MODIFY] [use-workspace-store.ts](file:///Users/azt/Desktop/Python/NotebookLLM/src/frontend-web/src/store/use-workspace-store.ts)
Add `galleryCollapsed: boolean` to `UiShellState`. Add `setGalleryCollapsed` and `toggleGalleryCollapsed` actions.

---

## Verification Plan

### Automated Tests

**Existing test:**
```bash
cd src/frontend-web && npx vitest run
```
The existing `use-workspace-store.test.ts` tests selection toggling and node position updates. These must continue to pass after the store changes.

**New test additions:**
- Add test cases for the new `galleryCollapsed` state toggle in `use-workspace-store.test.ts`.

**Build verification:**
```bash
cd src/frontend-web && npm run build
```
TypeScript compilation must succeed with zero errors. This validates all component prop contracts are satisfied.

### Browser Validation

Use the browser tool to verify visually:
1. **Auth flow:** Login page → register page → callback page all render correctly.
2. **Notebooks list:** Create, rename, delete all work. Cards use updated styling.
3. **Workspace page:** Source gallery on left, answer board center, studio slide-over right.
4. **Source upload/delete:** Upload zone in gallery works. Delete with confirm.
5. **Chat flow:** Send a message, see streaming response, citations appear.
6. **Studio panel:** Opens/closes, all 3 tabs accessible.
7. **Theme switching:** All 3 pastel themes render distinct and accessible.
8. **Responsive:** At 768px, gallery collapses, center takes full width, studio becomes a sheet.

### Manual Verification (User)
- Deploy locally and test podcast generation end-to-end (requires Kokoro TTS).
- Verify keyboard navigation works across gallery → answer board → studio.
- Test reduced-motion preference via OS settings.

---

## Open Questions

1. **Gallery rail width on desktop:** The spec says "Source Gallery rail" — should this be 280px (compact) or 320px (roomy)? This affects how much center space the answer board gets at 1440px.
2. **Studio panel behavior on tablet (768px-1024px):** Should studio become a bottom sheet (like mobile) or remain a narrower slide-over?
3. **Three.js removal:** Confirming this is safe. The `AmbientScene`, `KnowledgeNode`, and `KnowledgeThread` components appear unused in the current rendering tree, but I want to verify there's no dynamic import or lazy load I've missed. Should I do a final grep before proceeding?
