from templates_config import templates
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
import auth as auth_utils
import models
from datetime import datetime

router = APIRouter()

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/auth/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = auth_utils.authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(request, "login.html", {
            "error": "Invalid email or password"
        }, status_code=401)

    user.last_login = datetime.utcnow()
    db.commit()

    token = auth_utils.create_access_token(data={"sub": user.email})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("access_token", f"Bearer {token}", httponly=True, max_age=3600 * 8)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response
