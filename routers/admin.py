from templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_user
import models

router = APIRouter()

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    if current_user.role not in ["super_admin", "org_admin", "state_admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    states = db.query(models.State).all()
    courts = db.query(models.Court).all()
    case_types = db.query(models.CaseType).all()
    users = db.query(models.User).order_by(models.User.full_name).all()
    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    return templates.TemplateResponse(request, "admin/index.html", {
        "current_user": current_user,
        "states": states,
        "courts": courts,
        "case_types": case_types,
        "users": users,
        "roles": [r.value for r in models.UserRole],
        "unread_notifs": unread_notifs,
    })


@router.post("/admin/states/create")
async def create_state(
    name: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    if current_user.role not in ["super_admin", "org_admin"]:
        raise HTTPException(status_code=403)
    db.add(models.State(name=name, code=code.upper()))
    db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.post("/admin/case-types/create")
async def create_case_type(
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    if current_user.role not in ["super_admin", "org_admin"]:
        raise HTTPException(status_code=403)
    db.add(models.CaseType(name=name, description=description))
    db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.post("/admin/users/{user_id}/toggle-active")
async def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    if current_user.role not in ["super_admin", "org_admin"]:
        raise HTTPException(status_code=403)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)
