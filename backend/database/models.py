from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, ForeignKey, UniqueConstraint, Float, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import datetime

from .connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(100), nullable=False, default="v1")
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=True)  # Trading password for order operations
    
    # USD currency fields (US market only)
    initial_capital = Column(DECIMAL(18, 2), nullable=False, default=100000.00)
    current_cash = Column(DECIMAL(18, 2), nullable=False, default=100000.00)
    frozen_cash = Column(DECIMAL(18, 2), nullable=False, default=0.00)
    
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    positions = relationship("Position", back_populates="user")
    orders = relationship("Order", back_populates="user")
    auth_sessions = relationship("UserAuthSession", back_populates="user")


class UserAuthSession(Base):
    __tablename__ = "user_auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    user = relationship("User", back_populates="auth_sessions")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(100), nullable=False, default="v1")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(DECIMAL(18, 6), nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    user = relationship("User", back_populates="positions")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(100), nullable=False, default="v1")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_no = Column(String(32), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)
    side = Column(String(10), nullable=False)
    order_type = Column(String(20), nullable=False)
    price = Column(DECIMAL(18, 6))
    quantity = Column(Integer, nullable=False)
    filled_quantity = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    user = relationship("User", back_populates="orders")
    trades = relationship("Trade", back_populates="order")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(10), nullable=False)
    side = Column(String(10), nullable=False)
    price = Column(DECIMAL(18, 6), nullable=False)
    quantity = Column(Integer, nullable=False)
    commission = Column(DECIMAL(18, 6), nullable=False, default=0)
    trade_time = Column(TIMESTAMP, server_default=func.current_timestamp())

    order = relationship("Order", back_populates="trades")


class TradingConfig(Base):
    __tablename__ = "trading_configs"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(100), nullable=False, default="v1")
    market = Column(String(10), nullable=False)
    min_commission = Column(Float, nullable=False)
    commission_rate = Column(Float, nullable=False)
    exchange_rate = Column(Float, nullable=False, default=1.0)
    min_order_quantity = Column(Integer, nullable=False, default=1)
    lot_size = Column(Integer, nullable=False, default=1)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    __table_args__ = (UniqueConstraint('market', 'version'),)


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(String(5000), nullable=True)  # 增加到5000字符以支持长cookie
    description = Column(String(500), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )


class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market = Column(String(10), nullable=False, default="US")
    price = Column(DECIMAL(18, 6), nullable=False)
    price_date = Column(Date, nullable=False, index=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    __table_args__ = (UniqueConstraint('symbol', 'market', 'price_date'),)


class StockKline(Base):
    __tablename__ = "stock_klines"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market = Column(String(10), nullable=False, default="US")
    period = Column(String(10), nullable=False)  # 1m, 5m, 15m, 30m, 1h, 1d
    timestamp = Column(Integer, nullable=False, index=True)
    datetime_str = Column(String(50), nullable=False)
    open_price = Column(DECIMAL(18, 6), nullable=True)
    high_price = Column(DECIMAL(18, 6), nullable=True)
    low_price = Column(DECIMAL(18, 6), nullable=True)
    close_price = Column(DECIMAL(18, 6), nullable=True)
    volume = Column(DECIMAL(18, 2), nullable=True)
    amount = Column(DECIMAL(18, 2), nullable=True)
    change = Column(DECIMAL(18, 6), nullable=True)
    percent = Column(DECIMAL(10, 4), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    __table_args__ = (UniqueConstraint('symbol', 'market', 'period', 'timestamp'),)


# US market trading configuration constants
US_MIN_COMMISSION = 1.0  # $1 minimum commission
US_COMMISSION_RATE = 0.005  # 0.5% commission rate
US_MIN_ORDER_QUANTITY = 1
US_LOT_SIZE = 1
