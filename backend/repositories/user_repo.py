from sqlalchemy.orm import Session
from typing import Optional
from database.models import User, UserAuthSession
from decimal import Decimal
import hashlib
import secrets
import datetime


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


def _hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def set_user_password(db: Session, user_id: int, password: str) -> Optional[User]:
    """Set or update user trading password"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    user.password = _hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def verify_user_password(db: Session, user_id: int, password: str) -> bool:
    """Verify user trading password"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.password:
        return False
    
    return user.password == _hash_password(password)


def user_has_password(db: Session, user_id: int) -> bool:
    """Check if user has set a trading password"""
    user = db.query(User).filter(User.id == user_id).first()
    return user is not None and user.password is not None and user.password.strip() != ""


def create_auth_session(db: Session, user_id: int) -> Optional[UserAuthSession]:
    """Create a new authentication session for user (180 days expiry)"""
    # Clean up expired sessions for this user
    cleanup_expired_sessions(db, user_id)
    
    # Generate session token
    session_token = secrets.token_urlsafe(32)
    
    # Set expiry to 180 days from now
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=180)
    
    # Create session
    session = UserAuthSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


def verify_auth_session(db: Session, session_token: str) -> Optional[int]:
    """Verify session token and return user_id if valid"""
    session = db.query(UserAuthSession).filter(
        UserAuthSession.session_token == session_token,
        UserAuthSession.expires_at > datetime.datetime.utcnow()
    ).first()
    
    return session.user_id if session else None


def cleanup_expired_sessions(db: Session, user_id: int = None) -> int:
    """Clean up expired sessions. If user_id provided, clean only for that user"""
    query = db.query(UserAuthSession).filter(
        UserAuthSession.expires_at <= datetime.datetime.utcnow()
    )
    
    if user_id:
        query = query.filter(UserAuthSession.user_id == user_id)
    
    deleted_count = query.count()
    query.delete()
    db.commit()
    
    return deleted_count


def revoke_auth_session(db: Session, session_token: str) -> bool:
    """Revoke a specific session token"""
    session = db.query(UserAuthSession).filter(
        UserAuthSession.session_token == session_token
    ).first()
    
    if session:
        db.delete(session)
        db.commit()
        return True
    
    return False


def revoke_all_user_sessions(db: Session, user_id: int) -> int:
    """Revoke all sessions for a user"""
    deleted_count = db.query(UserAuthSession).filter(
        UserAuthSession.user_id == user_id
    ).count()
    
    db.query(UserAuthSession).filter(
        UserAuthSession.user_id == user_id
    ).delete()
    
    db.commit()
    return deleted_count
