from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUserDep, hash_password, new_token, verify_password
from app.db import get_db
from app.models import User
from app.schemas import AuthRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])

DbDep = Annotated[Session, Depends(get_db)]


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(db: DbDep, body: AuthRequest) -> AuthResponse:
    username = body.username.strip()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "That username is already taken")

    user = User(
        username=username,
        password_hash=hash_password(body.password),
        token=new_token(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=user.token, username=user.username)


@router.post("/login", response_model=AuthResponse)
def login(db: DbDep, body: AuthRequest) -> AuthResponse:
    user = db.scalar(select(User).where(User.username == body.username.strip()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")

    user.token = new_token()
    db.commit()
    return AuthResponse(token=user.token, username=user.username)


@router.post("/logout", status_code=204)
def logout(db: DbDep, user: CurrentUserDep) -> None:
    user.token = None
    db.commit()
