from templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from database import get_db
from auth import require_user
import models
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/actions", response_class=HTMLResponse)
async def actions_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    status: str = Query(""),
    priority: str = Query(""),
    filter: str = Query("all"),
):
    now = datetime.utcnow()

    # Auto-mark overdue
    overdue = db.query(models.Action).filter(
        models.Action.due_date < now,
        models.Action.status.in_(["Not Started", "In Progress"]),
        models.Action.is_deleted == False
    ).all()
    for a in overdue:
        a.status = models.ActionStatus.overdue.value
    if overdue:
        db.commit()

    q = db.query(models.Action).filter(models.Action.is_deleted == False).options(
        joinedload(models.Action.case),
        joinedload(models.Action.assigned_to_user)
    )

    if current_user.role in ["lawyer", "case_manager", "stakeholder"]:
        q = q.filter(models.Action.assigned_to_id == current_user.id)

    if status:
        q = q.filter(models.Action.status == status)
    if priority:
        q = q.filter(models.Action.priority == priority)

    if filter == "overdue":
        q = q.filter(models.Action.status == "Overdue")
    elif filter == "due_today":
        today_end = now.replace(hour=23, minute=59, second=59)
        q = q.filter(models.Action.due_date <= today_end, models.Action.due_date >= now.replace(hour=0, minute=0, second=0))
    elif filter == "due_soon":
        q = q.filter(models.Action.due_date >= now, models.Action.due_date <= now + timedelta(days=7))

    actions = q.order_by(models.Action.due_date).all()

    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    return templates.TemplateResponse(request, "actions.html", {
        "current_user": current_user,
        "actions": actions,
        "status_filter": status,
        "priority_filter": priority,
        "current_filter": filter,
        "statuses": [s.value for s in models.ActionStatus],
        "priorities": [p.value for p in models.CasePriority],
        "unread_notifs": unread_notifs,
        "now": now,
    })


@router.post("/actions/{action_id}/complete")
async def complete_action(
    action_id: int,
    completion_notes: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    action = db.query(models.Action).filter(models.Action.id == action_id).first()
    if action:
        action.status = models.ActionStatus.completed.value
        action.completion_date = datetime.utcnow()
        action.completion_notes = completion_notes
        db.commit()
    return RedirectResponse(url="/actions", status_code=302)


@router.post("/actions/{action_id}/update-status")
async def update_action_status(
    action_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    action = db.query(models.Action).filter(models.Action.id == action_id).first()
    if action:
        action.status = status
        if status == "Completed":
            action.completion_date = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/actions", status_code=302)
