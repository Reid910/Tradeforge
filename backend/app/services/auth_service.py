import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import generate_token
from app.models.magic_link_token import MagicLinkToken
from app.models.user import User
from app.services.map_service import seed_user_map


def _unique_username(db: Session, base: str) -> str:
    base = base[:24] or "player"
    candidate = base
    while db.query(User).filter(User.username == candidate).first() is not None:
        candidate = f"{base}_{secrets.token_hex(2)}"
    return candidate


def create_magic_link(db: Session, email: str) -> tuple[MagicLinkToken, str]:
    token_value = generate_token()
    token = MagicLinkToken(
        email=email,
        token=token_value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token, token_value


def confirm_magic_link(db: Session, token_value: str) -> User:
    token = db.execute(select(MagicLinkToken).where(MagicLinkToken.token == token_value)).scalar_one_or_none()

    if token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

    now = datetime.now(timezone.utc)
    if token.used_at is not None or token.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired link")

    token.used_at = now

    user = db.query(User).filter(User.email == token.email).first()
    is_new_user = user is None
    if user is None:
        username = _unique_username(db, token.email.split("@")[0])
        user = User(username=username, email=token.email, is_guest=False)
        db.add(user)
        db.commit()
        db.refresh(user)

    db.commit()

    if is_new_user:
        seed_user_map(db, user.id)

    return user


def create_guest_user(db: Session) -> User:
    username = _unique_username(db, f"guest_{secrets.token_hex(3)}")
    user = User(username=username, email=None, is_guest=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    seed_user_map(db, user.id)
    return user
