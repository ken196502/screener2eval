from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from database.connection import engine, Base, SessionLocal
from database.models import TradingConfig, User, SystemConfig
from config.settings import DEFAULT_TRADING_CONFIGS
app = FastAPI(title="Simulated US Stocks Trading API")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Trading API is running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，或指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.on_event("startup")
def on_startup():
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Seed trading configs if empty
    db: Session = SessionLocal()
    try:
        if db.query(TradingConfig).count() == 0:
            for cfg in DEFAULT_TRADING_CONFIGS.values():
                db.add(
                    TradingConfig(
                        version="v1",
                        market=cfg.market,
                        min_commission=cfg.min_commission,
                        commission_rate=cfg.commission_rate,
                        exchange_rate=cfg.exchange_rate,
                        min_order_quantity=cfg.min_order_quantity,
                        lot_size=cfg.lot_size,
                    )
                )
            db.commit()
        # Ensure a demo user exists
        if db.query(User).count() == 0:
            demo = User(
                version="v1",
                username="demo",
                initial_capital=200.0,
                current_cash=200.0,
                frozen_cash=0.0,
            )
            db.add(demo)
            db.commit()
    finally:
        db.close()
    
    # Start order scheduler
    from services.order_scheduler import start_order_scheduler
    start_order_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    # Stop order scheduler
    from services.order_scheduler import stop_order_scheduler
    stop_order_scheduler()


# API routes
from api.market_data_routes import router as market_data_router
from api.order_routes import router as order_router
from api.account_routes import router as account_router
from api.config_routes import router as config_router
from api.news_routes import router as news_router
from api.ranking_routes import router as ranking_router

app.include_router(market_data_router)
app.include_router(order_router)
app.include_router(account_router)
app.include_router(config_router)
app.include_router(news_router)
app.include_router(ranking_router)

# WebSocket endpoint
from api.ws import websocket_endpoint

app.websocket("/ws")(websocket_endpoint)

# Serve frontend index.html for root and SPA routes
@app.get("/")
async def serve_root():
    """Serve the frontend index.html for root route"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "Frontend not built yet"}

# Catch-all route for SPA routing (must be last)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the frontend index.html for SPA routes that don't match API/static"""
    # Skip API and static routes
    if full_path.startswith("api") or full_path.startswith("static") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"message": "Frontend not built yet"}
