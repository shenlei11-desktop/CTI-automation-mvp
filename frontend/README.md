# CTI/ICS Triage Tool — web app

React + TypeScript + Vite + Tailwind CSS. Two pages: an overview (`/`) and an
interactive demo (`/demo`) that calls the FastAPI backend directly. See the
[project README](../README.md) for the full picture — this file only covers the
frontend itself.

## Development

```bash
npm install
npm run dev       # http://localhost:5173, expects the backend at http://localhost:8000
```

The backend's `cors_origins` setting (`app/config.py`) already allows the Vite dev
(`5173`) and preview (`4173`) ports. Override the API base URL with a `VITE_API_BASE_URL`
env var if the backend runs elsewhere; it defaults to `http://localhost:8000`.

## Scripts

- `npm run dev` — dev server with HMR
- `npm run build` — type-checks (`tsc -b`) then produces a production build in `dist/`
- `npm run lint` — `oxlint`
- `npm run preview` — serves the production build locally (what the Docker `web`
  service runs)

## Structure

```
src/
  api/          typed fetch client + TS types mirroring app/schemas/*.py
  pages/        HomePage.tsx, DemoPage.tsx
  components/   ArchitectureDiagram, StatusBadge, TraceTimeline, IOCTable,
                TechniqueList, SeverityCard, InputPanel, ExampleButtons
  lib/          style.ts (severity/status color mapping), examples.ts (canned demos)
```

`src/api/types.ts` is hand-kept in sync with the backend's Pydantic schemas — there's
no shared codegen step, so a backend field rename needs a matching edit here.
