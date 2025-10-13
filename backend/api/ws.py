from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Dict, Set
import json
import asyncio

from database.connection import SessionLocal
from repositories.user_repo import get_or_create_user, get_user
from repositories.order_repo import list_orders
from repositories.position_repo import list_positions
from services.asset_calculator import calc_positions_value
from services.market_data import get_last_price
# from services.order_executor import place_and_execute
from services.order_matching import create_order, check_and_execute_order
from database.models import Trade, Order, US_COMMISSION_RATE, US_MIN_COMMISSION


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        pass  # WebSocket is already accepted in the endpoint

    def register(self, user_id: int, websocket: WebSocket):
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def unregister(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        if user_id not in self.active_connections:
            return
        payload = json.dumps(message, ensure_ascii=False)
        for ws in list(self.active_connections[user_id]):
            try:
                await ws.send_text(payload)
            except Exception:
                # remove broken connection
                self.active_connections[user_id].discard(ws)


manager = ConnectionManager()


async def _send_snapshot(db: Session, user_id: int):
    user = get_user(db, user_id)
    if not user:
        return
    positions = list_positions(db, user_id)
    orders = list_orders(db, user_id)
    trades = (
        db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.trade_time.desc()).limit(200).all()
    )
    positions_value = calc_positions_value(db, user_id)
    
    overview = {
        "user": {
            "id": user.id,
            "username": user.username,
            "initial_capital": float(user.initial_capital),
            "current_cash": float(user.current_cash),
            "frozen_cash": float(user.frozen_cash),
        },
        "total_assets": positions_value + float(user.current_cash),
        "positions_value": positions_value,
    }
    # enrich positions with latest price and market value
    enriched_positions = []
    price_error_message = None
    
    for p in positions:
        try:
            price = get_last_price(p.symbol, p.market)
        except Exception as e:
            price = None
            # 收集价格获取错误信息，特别是cookie相关的错误
            error_msg = str(e)
            if "cookie" in error_msg.lower() and price_error_message is None:
                price_error_message = error_msg
        
        enriched_positions.append({
            "id": p.id,
            "user_id": p.user_id,
            "symbol": p.symbol,
            "name": p.name,
            "market": p.market,
            "quantity": p.quantity,
            "available_quantity": p.available_quantity,
            "avg_cost": float(p.avg_cost),
            "last_price": float(price) if price is not None else None,
            "market_value": (float(price) * p.quantity) if price is not None else None,
        })

    # 准备响应数据
    response_data = {
        "type": "snapshot",
        "overview": overview,
        "positions": enriched_positions,
        "orders": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "user_id": o.user_id,
                "symbol": o.symbol,
                "name": o.name,
                "market": o.market,
                "side": o.side,
                "order_type": o.order_type,
                "price": float(o.price) if o.price is not None else None,
                "quantity": o.quantity,
                "filled_quantity": o.filled_quantity,
                "status": o.status,
            }
            for o in orders
        ],
        "trades": [
            {
                "id": t.id,
                "order_id": t.order_id,
                "user_id": t.user_id,
                "symbol": t.symbol,
                "name": t.name,
                "market": t.market,
                "side": t.side,
                "price": float(t.price),
                "quantity": t.quantity,
                "commission": float(t.commission),
                "trade_time": str(t.trade_time),
            }
            for t in trades
        ],
    }
    
    # 如果有价格获取错误，添加警告信息
    if price_error_message:
        response_data["warning"] = {
            "type": "market_data_error",
            "message": price_error_message
        }
    
    await manager.send_to_user(user_id, response_data)


async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id: int | None = None
    # background periodic snapshot task
    periodic_task = None
    async def periodic_snapshot():
        while True:
            try:
                await asyncio.sleep(10)
                if user_id is None:
                    continue
                db: Session = SessionLocal()
                try:
                    await _send_snapshot(db, user_id)
                finally:
                    db.close()
            except Exception:
                # ignore periodic errors
                pass
    try:
        periodic_task = asyncio.create_task(periodic_snapshot())
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            kind = msg.get("type")
            db: Session = SessionLocal()
            try:
                if kind == "bootstrap":
                    user = get_or_create_user(
                        db, 
                        msg.get("username", "demo"),
                        float(msg.get("initial_capital", 100000))
                    )
                    user_id = user.id
                    manager.register(user_id, websocket)
                    await manager.send_to_user(user_id, {"type": "bootstrap_ok", "user": {"id": user.id, "username": user.username}})
                    await _send_snapshot(db, user_id)
                elif kind == "subscribe":
                    # subscribe existing user_id
                    uid = int(msg.get("user_id"))
                    u = get_user(db, uid)
                    if not u:
                        await websocket.send_text(json.dumps({"type": "error", "message": "user not found"}))
                        continue
                    user_id = uid
                    manager.register(user_id, websocket)
                    await _send_snapshot(db, user_id)
                elif kind == "place_order":
                    if user_id is None:
                        await websocket.send_text(json.dumps({"type": "error", "message": "not bootstrapped"}))
                        continue
                    user = get_user(db, user_id)
                    try:
                        order = create_order(
                            db=db,
                            user=user,
                            symbol=msg["symbol"],
                            name=msg.get("name", msg["symbol"]),
                            market=msg["market"],
                            side=msg["side"],
                            order_type=msg.get("order_type", "MARKET"),
                            price=msg.get("price"),
                            quantity=int(msg["quantity"])
                        )
                        # 对于限价买入，冻结预估成交金额（市价或限价取较小）+ 佣金；对于市价买入，按市价估算
                        if order.side == "BUY":
                            try:
                                market_price = get_last_price(order.symbol, order.market)
                            except Exception:
                                market_price = order.price or 0.0
                            ref_price = min(float(order.price) if order.price else float(market_price), float(market_price) if market_price else float(order.price or 0.0)) or float(order.price or market_price or 0.0)
                            notional = ref_price * order.quantity
                            commission = max(notional * float(US_COMMISSION_RATE), float(US_MIN_COMMISSION))
                            user.frozen_cash = float(user.frozen_cash) + (notional + commission)
                            db.commit()
                        # 检查成交条件并尝试立即成交一次
                        executed = check_and_execute_order(db, order)
                        if executed:
                            await manager.send_to_user(user_id, {"type": "order_filled", "order_id": order.id})
                        else:
                            await manager.send_to_user(user_id, {"type": "order_pending", "order_id": order.id})
                        await _send_snapshot(db, user_id)
                    except ValueError as e:
                        await manager.send_to_user(user_id, {"type": "error", "message": str(e)})
                elif kind == "get_snapshot":
                    if user_id is not None:
                        await _send_snapshot(db, user_id)
                elif kind == "get_trades":
                    if user_id is not None:
                        trades = (
                            db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.trade_time.desc()).limit(200).all()
                        )
                        await manager.send_to_user(user_id, {
                            "type": "trades",
                            "trades": [
                                {
                                    "id": t.id,
                                    "order_id": t.order_id,
                                    "user_id": t.user_id,
                                    "symbol": t.symbol,
                                    "name": t.name,
                                    "market": t.market,
                                    "side": t.side,
                                    "price": float(t.price),
                                    "quantity": t.quantity,
                                    "commission": float(t.commission),
                                    "trade_time": str(t.trade_time),
                                }
                                for t in trades
                            ]
                        })
                elif kind == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "unknown message"}))
            finally:
                db.close()
    except WebSocketDisconnect:
        if user_id is not None:
            manager.unregister(user_id, websocket)
        return
    finally:
        try:
            if periodic_task:
                periodic_task.cancel()
        except Exception:
            pass
