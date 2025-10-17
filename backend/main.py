from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database.connection import engine, Base, SessionLocal
from database.models import TradingConfig, User, SystemConfig
from config.settings import DEFAULT_TRADING_CONFIGS
app = FastAPI(title="Simulated US Stocks Trading API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2621"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

app.include_router(market_data_router)
app.include_router(order_router)
app.include_router(account_router)
app.include_router(config_router)
app.include_router(news_router)

# WebSocket endpoint
from api.ws import websocket_endpoint

app.websocket("/ws")(websocket_endpoint)
