from templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_user, get_password_hash
import models

router = APIRouter()

@router.get("/people", response_class=HTMLResponse)
async def people_list(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    users = db.query(models.User).filter(models.User.is_active == True).order_by(models.User.full_name).all()
    states = db.query(models.State).all()
    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    return templates.TemplateResponse(request, "people.html", {
        "current_user": current_user,
        "users": users,
        "states": states,
        "roles": [r.value for r in models.UserRole],
        "unread_notifs": unread_notifs,
    })


@router.post("/people/create")
async def create_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    state_id: int = Form(None),
    designation: str = Form(""),
    phone: str = Form(""),
):
    if current_user.role not in ["super_admin", "org_admin", "state_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    user = models.User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        role=role,
        state_id=state_id if state_id else None,
        designation=designation,
        phone=phone,
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/people", status_code=302)
