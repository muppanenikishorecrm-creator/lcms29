from templates_config import templates
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_user
import models

router = APIRouter()

@router.get("/notifications", response_class=HTMLResponse)
async def notifications(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(100).all()

    unread_notifs = sum(1 for n in notifs if not n.is_read)

    return templates.TemplateResponse(request, "notifications.html", {
        "current_user": current_user,
        "notifications": notifs,
        "unread_notifs": unread_notifs,
    })


@router.get("/notifications/mark-all-read")
async def mark_all_read(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return RedirectResponse(url="/notifications", status_code=302)


@router.get("/notifications/{notif_id}/read")
async def mark_read(notif_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notif_id,
        models.Notification.user_id == current_user.id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
    return RedirectResponse(url="/notifications", status_code=302)
