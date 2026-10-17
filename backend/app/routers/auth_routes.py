from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import COOKIE, MAX_AGE, check_password, current_user, make_token
from app.db import get_db
from app.models import AdminUser

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == body.username.strip()).one_or_none()
    recognised = check_password(body.password, user)
    if user is None or not recognised:
        raise HTTPException(status_code=401, detail="Those details were not recognised")
    response.set_cookie(
        COOKIE,
        make_token(user.username),
        httponly=True,
        samesite="lax",
        max_age=MAX_AGE,
        path="/",
    )
    return {"username": user.username}


@router.post("/logout")
def logout(response: Response, _: AdminUser = Depends(current_user)):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: AdminUser = Depends(current_user)):
    return {"username": user.username}
