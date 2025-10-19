# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack simulated US stock trading application built as a monorepo. The application features real-time trading with WebSocket-driven frontend communication and a sophisticated backend order matching system.

### Tech Stack
- **Backend**: FastAPI + Uvicorn, SQLAlchemy, SQLite, background scheduler
- **Frontend**: React (Vite) + Tailwind CSS + shadcn/ui
- **Realtime**: WebSocket communication for live market data and order updates
- **Package Management**: pnpm (frontend) + uv (backend)

## Common Development Commands

### Installation & Setup
```bash
# Install all dependencies (JS + Python)
pnpm run install:all

# Alternative for JS dependencies only
pnpm install

# Alternative for Python dependencies only
cd backend && uv sync
```

### Development Servers
```bash
# Run both frontend and backend simultaneously
pnpm run dev

# Run backend only (port 2611)
pnpm run dev:backend

# Run frontend only (port 2621)
pnpm run dev:frontend
```

### Building & Testing
```bash
# Build frontend
pnpm run build

# Run backend tests (if any exist)
cd backend && python -m pytest

# Lint and format
cd backend && ruff check .
cd backend && black .
```

## Architecture Overview

### Backend Structure
The backend follows a layered architecture with clear separation of concerns:

#### Core Components
- **Entry Point**: `main.py` - FastAPI application startup and middleware configuration
- **Database Models**: `database/models.py` - User, Position, Order, Trade, TradingConfig, StockPrice, StockKline
- **WebSocket Endpoint**: `api/ws.py` - Real-time communication via `/ws` endpoint
- **HTTP Routes**: `api/*.py` - RESTful API endpoints for orders, account, market data, etc.

#### Service Layer (`services/`)
- **order_matching.py**: Core order creation, validation, and execution logic
- **market_data.py**: Price data fetching from external APIs (Xueqiu, Zhitong)
- **order_scheduler.py**: Background task scheduler for order processing
- **asset_calculator.py**: Portfolio valuation and position calculations
- **xueqiu_market_data.py**: Xueqiu API integration for real-time stock prices
- **cookie_helper.py**: Authentication cookie management for external APIs

#### Repository Layer (`repositories/`)
Data access layer for database operations.

#### Configuration
- **Frontend URLs**: Configured for ports 2621 (frontend) / 2611 (backend by default)
- **Database**: SQLite at `backend/data.db`
- **CORS**: Configured to allow localhost connections

### Frontend Structure
- **Entry Point**: `frontend/app/main.tsx` - Application initialization and WebSocket connection
- **Build Tool**: Vite with development server on port 2621
- **UI Framework**: React with Tailwind CSS and shadcn/ui components
- **Real-time**: WebSocket singleton for managing live connections

### Key Business Logic

#### Order Processing
- **Commission**: max(0.5% of notional, $1.00) for US market
- **Lot Size**: 1 share
- **Minimum Order**: 1 share
- **Cash Management**: BUY orders freeze estimated funds; SELL requires position check
- **Execution**: Immediate execution attempt + periodic background processing

#### Market Data
- **Supported Symbols**: AAPL.US, TSLA.US, MSFT.US, GOOGL.US, AMZN.US, NVDA.US, META.US
- **Price Sources**: Real-time fetching from Xueqiu API
- **Error Handling**: Graceful degradation when price data unavailable

#### WebSocket Protocol
Real-time state synchronization via WebSocket messages:
- `bootstrap` - User creation/session setup
- `place_order` - Order submission and immediate execution
- `get_snapshot` - Portfolio state retrieval
- `subscribe` - User session attachment
- `ping/pong` - Connection health checks

### Data Models

#### Core Entities
- **User**: Trading account with USD balances (initial_cash, current_cash, frozen_cash)
- **Position**: Stock holdings with average cost tracking
- **Order**: Buy/sell orders with status tracking (PENDING/FILLED/CANCELLED)
- **Trade**: Executed order records with commission tracking
- **TradingConfig**: Market-specific trading rules and fees

#### Database Schema
- SQLite database with proper indexing
- Versioned entities (User, Position, Order, TradingConfig)
- Unique constraints for business integrity
- Timestamp fields for audit trail

### Authentication & Sessions
- **Demo User**: Auto-created "demo" user with $100k starting capital
- **Session Management**: WebSocket-based user registration system
- **No Traditional Auth**: Simplified for demo purposes

## Important Notes

### Port Configuration
- By default: Backend on 2611, Frontend on 2621
- Port mismatch causes connection errors
- Frontend WebSocket URL: `ws://localhost:2621/ws`
- API_BASE: `http://localhost:2621`

### Data Sources and Web Scraping
**Market Data & Stock Information**:
- **Source**: Xueqiu.com (雪球网) - Chinese investment social platform
- **Method**: Reverse engineering web APIs and authentication mechanisms
- **Data**: Real-time stock prices, K-line data, and market information for US stocks
- **Authentication**: Cookie-based session management with `cookie_helper.py`
- **Supported Tickers**: AAPL.US, TSLA.US, MSFT.US, GOOGL.US, AMZN.US, NVDA.US, META.US

**News Data**:
- **Source**: GMTEight.com (gmteight.com) - Financial news platform
- **Method**: Reverse engineering web scraping techniques
- **Content**: Stock market news and related financial information
- **Integration**: News routing service (`news_routes.py`) for news aggregation

**Important**: The system relies on reverse-engineered web APIs and may be affected by:
- Platform API changes that break existing endpoints
- Authentication requirement updates (cookie validity)
- Rate limiting or anti-bot measures
- Geographic access restrictions

### Development Environment
- **Python 3.10+** required with `uv` package manager
- **Node.js 18+** required with `pnpm`
- **React StrictMode** may cause duplicate WebSocket connections (handled with singleton)
- **Live Market Data** requires internet access for external API calls

### Troubleshooting
- **Connection Issues**: Verify port configuration and CORS settings
- **Price Data Failures**: Check external API connectivity and authentication cookies
- **Database Permissions**: Ensure write access to `backend/data.db`
- **Order Processing**: Monitor background scheduler and order matching logs

## Financial Calculations

### Position Valuation
```
Market Value = Quantity × Last Price
Total Assets = Current Cash + Frozen Cash + Positions Value
```

### Commission Calculation
```
Commission = max(Commission_Rate × Notional, Minimum_Commission)
Notional = Execution_Price × Quantity
```

### Order Impact
- **BUY**: Freezes (estimated_notional + commission), updates position on fill
- **SELL**: Validates available quantity, releases position on fill
- **CANCEL**: Releases frozen funds for pending orders

This system simulates realistic US market trading mechanics with proper position management, cash reconciliation, and commission handling.