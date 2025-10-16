# Repository Guidelines

## Project Structure & Module Organization
The monorepo centers on `backend` for the FastAPI service and `frontend` for the Vite/React client. Backend routing lives in `backend/api`, domain logic in `backend/services`, persistence in `backend/database` and `backend/repositories`, and pydantic contracts in `backend/schemas`. Frontend UI components reside under `frontend/app/components`, while shared utilities and hooks sit in `frontend/app/lib`. Workspace-level scripts in `package.json` orchestrate both layers; treat `demo_trading.db` as disposable local state.

## Build, Test, and Development Commands
Run `pnpm run install:all` once to install JS dependencies and sync the uv-managed Python environment. `pnpm run dev` boots both servers (backend on 2611, frontend on 2621). Use `pnpm run dev:backend` or `pnpm run dev:frontend` when iterating on a single tier. `pnpm run build` bundles the frontend (backend build step is currently a no-op placeholder). For an isolated backend session: `uv run uvicorn main:app --reload --port 2611 --host 0.0.0.0`.

## Coding Style & Naming Conventions
Python code follows Black/PEP 8 formatting; run `uv run black backend` before submitting. Lint backend modules with `uv run ruff check backend`. Prefer descriptive module names (e.g., `order_matching.py`) and PascalCase for Pydantic models. Frontend files should stay in TypeScript `.tsx` form, use PascalCase for components inside `frontend/app/components`, and keep Tailwind classes grouped by layout → color → effects.

## Testing Guidelines
Pytest is declared in `backend/pyproject.toml`; place unit tests under `backend/tests` with filenames like `test_order_matching.py`. Target business-critical services (`backend/services/order_matching.py`, `backend/api/ws.py`) first and mock external APIs. No automated frontend tests exist yet; when adding them, colocate Vitest files beside the component (`OrderTable.test.tsx`) and ensure they run without the backend by stubbing WebSocket calls.

## Commit & Pull Request Guidelines
Git history favors short, imperative summaries (`add pie chart`, `improve trade logic`). Keep messages under 60 characters and expand on breaking details in the body when needed. Pull requests should link tracking issues, describe the scenario under test, and include screenshots or terminal captures for UI or API changes. Mention any port or configuration adjustments so reviewers can reproduce.

## Security & Configuration Tips
Default URLs target backend HTTP on 2611 and WebSocket on 2621; mirror that in `frontend/app/main.tsx` when changing ports. Store secrets in local `.env` files and avoid committing database snapshots like `demo_trading.db`. When running against live data sources, throttle external requests in `backend/services/market_data.py` to stay within provider limits.
