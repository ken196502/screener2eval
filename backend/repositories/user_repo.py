from sqlalchemy.orm import Session
from typing import Optional
from database.models import User
from decimal import Decimal


def get_or_create_user(
    db: Session, 
    username: str, 
    initial_capital: float = 100000.0
) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(
        version="v1",
        username=username,
        initial_capital=initial_capital,
        current_cash=initial_capital,
        frozen_cash=0.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def update_user_cash(
    db: Session, 
    user_id: int, 
    current_cash: float, 
    frozen_cash: float = None
) -> Optional[User]:
    """Update user cash balance"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    user.current_cash = current_cash
    if frozen_cash is not None:
        user.frozen_cash = frozen_cash
    
    db.commit()
    db.refresh(user)
    return user
