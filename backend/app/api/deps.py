from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.mine_service import settle_all_mines


def get_current_user(
    db: Session = Depends(get_db),
    tf_session: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> User:
    if not tf_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = decode_access_token(tf_session)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def get_current_user_settled(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Same as get_current_user, but also auto-credits any mine production
    that's accrued since the user was last seen. Used by routes that touch
    mines/map/inventory so accrual happens passively instead of via a
    dedicated collect action.
    """
    settle_all_mines(db, current_user.id)
    return current_user
