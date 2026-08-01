from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import check_auth_rate_limit
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    MagicLinkConfirmRequest,
    MagicLinkRequest,
    MagicLinkRequestResponse,
    UserOut,
)
from app.services.auth_service import confirm_magic_link, create_guest_user, create_magic_link

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, user_id: int) -> None:
    token = create_access_token(user_id)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/magic-link", response_model=MagicLinkRequestResponse)
def request_magic_link(payload: MagicLinkRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    check_auth_rate_limit(f"{client_ip}:{payload.email.lower()}")

    _token, token_value = create_magic_link(db, payload.email)
    confirm_link = f"{settings.frontend_url}/auth/confirm?token={token_value}"

    if settings.is_production:
        # TODO: wire up real email delivery (SMTP/SES/Resend) before deploying.
        print(f"[magic-link] would email {payload.email}: {confirm_link}")
        return MagicLinkRequestResponse(message="Check your email for a sign-in link.")

    print(f"[magic-link:dev] {payload.email} -> {confirm_link}")
    return MagicLinkRequestResponse(
        message="Dev mode: no email sent, use the link below.",
        dev_magic_link=confirm_link,
    )


@router.post("/magic-link/confirm", response_model=UserOut)
def confirm_magic_link_endpoint(
    payload: MagicLinkConfirmRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    user = confirm_magic_link(db, payload.token)
    _set_session_cookie(response, user.id)
    return user


@router.post("/guest", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def guest_login(response: Response, db: Session = Depends(get_db)) -> User:
    user = create_guest_user(db)
    _set_session_cookie(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name, path="/")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
