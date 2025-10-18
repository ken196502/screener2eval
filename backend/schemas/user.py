from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    initial_capital: float = 100000.0


class UserOut(BaseModel):
    id: int
    username: str
    initial_capital: float
    current_cash: float
    frozen_cash: float
    has_password: bool = False  # Indicates if user has set a trading password

    class Config:
        from_attributes = True


class PasswordSetRequest(BaseModel):
    password: str


class PasswordVerifyRequest(BaseModel):
    password: str


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthSessionResponse(BaseModel):
    session_token: str
    expires_at: str  # ISO format datetime string
    message: str


class AuthVerifyRequest(BaseModel):
    session_token: str


class AccountOverview(BaseModel):
    user: UserOut
    total_assets: float  # Total assets in USD
    positions_value: float  # Total positions value in USD
