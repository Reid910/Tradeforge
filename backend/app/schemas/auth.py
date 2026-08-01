from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkRequestResponse(BaseModel):
    message: str
    dev_magic_link: str | None = None


class MagicLinkConfirmRequest(BaseModel):
    token: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    is_guest: bool
    balance: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}