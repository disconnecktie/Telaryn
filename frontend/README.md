# Telaryn Frontend

The Telaryn frontend is a React application built with Vite. It presents the
authenticated work-management experience while treating the FastAPI backend as
the authority for identity, workspace access, workflow validation, derived
project state, and durable mutations.

## Run locally

From this directory:

```powershell
npm install
npm run dev
```

The default development UI runs at `http://localhost:5173`. Start the backend
from the repository root and keep the configured frontend origin aligned with
the backend's allowed origins.

## Quality checks

Run the same frontend checks used by CI:

```powershell
npm ci
npm run lint
npm test
npm run build
```

Tests use Vitest, React Testing Library, and jsdom. They should describe visible
user behavior and mock the API module boundary instead of coupling assertions to
component internals.

## Responsibility boundaries

- `src/api.js` owns HTTP communication and response normalization.
- `src/views/` owns page-level presentation.
- `src/components/` owns focused reusable workflows and sections.
- `src/hooks/` owns reusable stateful behavior and derived loading concerns.
- `src/App.jsx` coordinates shared navigation, separate active/archived data,
  archive/restore operations, and other authoritative workflows; it should not
  absorb derived state that belongs in the backend or presentation that has a
  clear component owner.
- `src/styles/` owns the visual system and responsive behavior.

The detailed ownership inventory lives in
[`docs/frontend-responsibility-map.md`](../docs/frontend-responsibility-map.md).

## Change expectations

Frontend controls may stage or request work, but they are never an authorization
boundary. New mutation paths must reuse backend validation, workspace isolation,
transactional behavior, and audit semantics. Responsive behavior should be
verified at both narrow and full-width layouts, and user-facing behavior changes
should update the root README, architecture notes, roadmap or handoff when
applicable, and the changelog.

