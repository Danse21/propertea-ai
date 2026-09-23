import secrets
from typing import Annotated

import bcrypt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def current_user(
    db: Annotated[Session, Depends(get_db)],
    x_session_id: Annotated[str | None, Header(alias="X-Session-Id")] = None,
) -> User:
    if not x_session_id:
        raise HTTPException(401, "Not authenticated")
    user = db.scalar(select(User).where(User.token == x_session_id))
    if user is None:
        raise HTTPException(401, "Invalid or expired session")
    return user


CurrentUserDep = Annotated[User, Depends(current_user)]
