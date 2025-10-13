# Strategy Simulator (PNPM + UV)

A full‑stack demo of a simulated US stock trading application. The app is realtime-first: the frontend talks to the backend primarily via a single WebSocket endpoint. A few HTTP endpoints are available for management actions (e.g., cancel an order).

Note: The frontend currently opens a WebSocket to ws://localhost: 2621/ws and calls HTTP at http://127.0.0.1:2611 by default. The monorepo scripts run the backend on port 2611 and the frontend on 2621. You can either:
- change the frontend URLs to 2611, or
- start the backend on  2621 instead.

See Configuration and Troubleshooting for details.

## Tech Stack
- Backend: FastAPI + Uvicorn, SQLAlchemy, SQLite, background scheduler
- Frontend: React (Vite) + Tailwind + shadcn/ui
- Realtime: WebSocket
- Package managers: pnpm (frontend root), uv (Python backend)

## Repository Structure
- backend/: FastAPI app, DB models, services
- frontend/: React application (Vite)
- package.json: workspace scripts to run both dev servers
- pnpm-workspace.yaml: workspace configuration

## Getting Started

### Prerequisites
- Node.js 18+ and pnpm
- Python 3.10+ and uv

### Install
```bash
# install JS deps and sync Python env
pnpm run install:all
```

### Development
By default, the workspace scripts launch:
- Backend on port 2611
- Frontend on port 2621

Start both dev servers:
```bash
pnpm run dev
```
Open:
- Frontend: http://localhost:2621
- Backend WS: ws://localhost:2611/ws

Important: The frontend source is currently configured for port  2621. To use the workspace defaults (2611), update the following in frontend/app/main.tsx:
- WebSocket URL: ws://localhost:2611/ws
- API_BASE: http://127.0.0.1:2611

Alternatively, run the backend on  2621:
```bash
# from repo root
cd backend
uv sync
uv run uvicorn main:app --reload --port  2621 --host 0.0.0.0
```

### Build
```bash
# build frontend; backend has no dedicated build step
pnpm run build
```
Static assets for the frontend are produced by Vite. The backend is a standard FastAPI app that can be run with Uvicorn or any ASGI server.

## Backend Overview

- Entry point: backend/main.py
- Database: SQLite at sqlite:///./data.db (see backend/database/connection.py)
- Models: User, Position, Order, Trade, TradingConfig (see backend/database/models.py)
- Services:
  - services/market_data.py: last price and K-line data via Xueqiu
  - services/order_matching.py: order validation, freezing/releasing cash, fills
  - services/order_scheduler.py: periodic processing of pending orders
  - services/asset_calculator.py: portfolio valuation helpers
- WebSocket endpoint: /ws (see backend/api/ws.py)
- HTTP routes: under /api (orders, account, market data)

Commission and trading rules (US market):
- Commission: max(0.5% of notional, $1.00)
- Lot size: 1 share
- Minimum order quantity: 1 share
- Buy orders freeze estimated notional + commission; on fill/cancel, cash is reconciled

### Market Data
Real prices are fetched from Xueqiu for a small set of symbols defined in services/market_data.py:
- AAPL.US, TSLA.US, MSFT.US, GOOGL.US, AMZN.US, NVDA.US, META.US

If a symbol is unsupported or the remote call fails, order placement/valuation may raise an error.

## WebSocket Protocol
The frontend opens a WebSocket and drives its UI from server messages.

Client → Server
```json
{ "type": "bootstrap", "username": "demo", "initial_capital": 100000 }
```

Server → Client
```json
{ "type": "bootstrap_ok", "user": { "id": 1, "username": "demo" } }
{ "type": "snapshot", "overview": { "user": {"id": 1, "username": "demo", "initial_capital": 100000, "current_cash": 100000, "frozen_cash": 0 }, "positions_value": 0, "total_assets": 100000 }, "positions": [], "orders": [], "trades": [] }
```

Supported client messages:
- bootstrap — create or load a user and register the socket
- subscribe — register the socket for an existing user_id
- place_order — place an order and attempt immediate execution
  - payload: { symbol, name, market, side, order_type, price?, quantity }
- get_snapshot — request the latest snapshot
- get_trades — request the latest trades
- ping — liveness check (server responds pong)

Server messages:
- bootstrap_ok — { user: { id, username } }
- snapshot — { overview, positions, orders, trades }
- trades — latest trades list
- order_filled — order fill notification (a fresh snapshot follows)
- order_pending — order is accepted but not yet filled
- error — { message }

## Order Lifecycle and Funds/Position Handling

This app simulates realistic order processing with cash freezing for BUY orders, position checks for SELL orders, and proper reconciliation on fill or cancel. Commission for US market is computed as:
- commission = max(commission_rate × notional, min_commission)
  - commission_rate = 0.005 (0.5%)
  - min_commission = $1.00
- notional = execution_price × quantity

Key order fields: side (BUY/SELL), order_type (MARKET/LIMIT), price (optional for LIMIT), quantity, status (PENDING/FILLED/CANCELLED), filled_quantity.

Symbols supported for live pricing are defined in services/market_data.py; unsupported symbols will raise errors.

### 1) Placing an order
- Common validations
  - Market must be US
  - Quantity must be >= 1 and a multiple of lot_size (1)
- BUY
  - On place, the server freezes an estimated amount in user.frozen_cash:
    - ref_price = min(limit_price, market_price) when both available; otherwise whichever is available
    - estimated_notional = ref_price × quantity
    - estimated_commission = max(commission_rate × estimated_notional, min_commission)
    - frozen_cash += estimated_notional + estimated_commission
  - Order is inserted with status = PENDING and filled_quantity = 0
- SELL
  - Requires available_quantity >= quantity for the symbol
  - No cash is frozen for SELL
  - Order is inserted with status = PENDING

After insertion, the system immediately tries to execute once. A background scheduler also periodically processes PENDING orders.

### 2) Execution logic (fills)
- Price source
  - MARKET: execution_price = latest market price
  - LIMIT: order matches and executes if market price is compatible with limit (e.g., BUY executes when market_price <= limit_price; SELL when market_price >= limit_price). If matched, execution_price is the current market price.
- BUY fill
  - notional = execution_price × quantity
  - commission = max(rate × notional, min)
  - Deduct current_cash by (notional + commission)
  - Update or create Position:
    - new_qty = old_qty + quantity
    - new_avg_cost = (old_avg_cost × old_qty + notional) / new_qty
    - available_quantity += quantity
  - Create Trade record
  - Release frozen: frozen_cash = max(frozen_cash − (notional + commission), 0)
  - Order: filled_quantity = quantity; status = FILLED
- SELL fill
  - Check available_quantity >= quantity
  - Update Position:
    - quantity -= quantity; available_quantity -= quantity
  - notional = execution_price × quantity
  - commission = max(rate × notional, min)
  - Add to current_cash: cash_gain = notional − commission
  - Create Trade record
  - Order: filled_quantity = quantity; status = FILLED

Note: This demo fills orders fully when conditions are met (no partial fills). The scheduler continues to check pending orders at intervals.

### 3) Cancellation
- Only PENDING orders can be cancelled
- BUY: release frozen funds conservatively using a reference price similar to placement:
  - ref_price = min(limit_price, latest_market_price) when both available
  - release_amount = (ref_price × quantity) + commission(ref_price × quantity)
  - frozen_cash = max(frozen_cash − release_amount, 0)
- SELL: nothing to release (no funds were frozen)
- Order status becomes CANCELLED

### 4) Snapshot updates
After placement, fills, or cancellation, the server pushes a fresh snapshot via WebSocket containing:
- overview: user balances (initial_capital, current_cash, frozen_cash), positions_value, total_assets
- positions: enriched with last_price and market_value
- orders: recent orders with status
- trades: recent trades

## HTTP API (Selected)
The frontend uses an HTTP cancel endpoint for pending orders:
- POST /api/orders/cancel/{order_id}

Account and market data routes also exist under /api (see backend/api/* for details).

## Frontend Overview
- Vite + React + Tailwind + shadcn/ui
- A module-level WebSocket singleton is used to avoid duplicate connections under React StrictMode
- UI state is driven by WS messages; no REST fetching for portfolio tables
- Trading panel supports LIMIT and MARKET orders. In MARKET mode, the displayed price follows the latest price from the server.

## Data and Seeding
On startup, the backend:
- Creates tables if missing
- Seeds trading configurations
- Ensures a demo user (demo) with $100,000 initial cash exists

To reset demo data, remove the SQLite file (data.db) and restart the backend.

## Configuration
- Ports (scripts): backend 2611, frontend 2621
- CORS: backend allows http://localhost:2621 by default
- Database URL: sqlite:///./data.db (file is created in backend working directory)
- Market data requires internet access to call Xueqiu

To switch the frontend to use port 2611, edit frontend/app/main.tsx:
- Replace ws://localhost: 2621/ws with ws://localhost:2611/ws
- Replace API_BASE http://127.0.0.1:2611 with http://127.0.0.1:2611

## Troubleshooting
- Port mismatch: if you see connection errors, ensure the frontend WS URL and API_BASE match the backend port.
- Duplicate connect/disconnect: React StrictMode mounts components twice in dev. A WS singleton is used; when the server closes the socket, the singleton resets so a new connection can be established later.
- Unsupported symbols or market data failures: only the listed US tickers are supported. Network issues or API limits may cause price fetch errors.
- Database location: ensure the process has write permissions for data.db.

## Scripts Reference
From repo root (package.json):
- dev: concurrently run backend (2611) and frontend (2621)
- dev:backend: uv sync, then uvicorn main:app --reload --port 2611
- dev:frontend: vite --port 2621
- install:all: pnpm install and uv sync

From frontend (frontend/package.json):
- dev: vite --port 2621
- build: vite build

## License
For demo purposes only.
