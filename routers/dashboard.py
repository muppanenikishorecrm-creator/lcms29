from templates_config import templates
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from database import get_db
from auth import require_user
import models
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    now = datetime.utcnow()
    seven_days = now + timedelta(days=7)

    total_cases = db.query(models.Case).filter(models.Case.is_deleted == False).count()
    active_cases = db.query(models.Case).filter(
        models.Case.is_deleted == False,
        models.Case.status.in_(["Active", "Hearing / Action Pending", "Awaiting Order", "Order Received", "Compliance / Follow-up"])
    ).count()
    new_cases = db.query(models.Case).filter(
        models.Case.is_deleted == False,
        models.Case.status == "New"
    ).count()
    closed_cases = db.query(models.Case).filter(
        models.Case.is_deleted == False,
        models.Case.status.in_(["Closed", "Resolved"])
    ).count()
    critical_cases = db.query(models.Case).filter(
        models.Case.is_deleted == False,
        models.Case.priority == "Critical"
    ).count()

    upcoming_hearings = db.query(models.Hearing).filter(
        models.Hearing.hearing_date >= now,
        models.Hearing.hearing_date <= seven_days
    ).count()

    overdue_actions = db.query(models.Action).filter(
        models.Action.is_deleted == False,
        models.Action.status == "Overdue"
    ).count()

    actions_due = db.query(models.Action).filter(
        models.Action.is_deleted == False,
        models.Action.due_date >= now,
        models.Action.due_date <= seven_days,
        models.Action.status.in_(["Not Started", "In Progress"])
    ).count()

    # My personal stats
    my_cases_count = 0
    my_overdue = 0
    my_upcoming_hearings = 0
    my_due_soon = 0
    my_unread_notifs = 0
    cases_without_updates = 0

    if current_user.role in ["lawyer", "case_manager", "stakeholder"]:
        my_assignments = db.query(models.CaseAssignment).filter(
            models.CaseAssignment.user_id == current_user.id,
            models.CaseAssignment.is_active == True
        ).all()
        my_case_ids = [a.case_id for a in my_assignments]
        my_cases_count = len(set(my_case_ids))

        my_overdue = db.query(models.Action).filter(
            models.Action.case_id.in_(my_case_ids),
            models.Action.status == "Overdue",
            models.Action.is_deleted == False
        ).count()

        my_due_soon = db.query(models.Action).filter(
            models.Action.case_id.in_(my_case_ids),
            models.Action.due_date >= now,
            models.Action.due_date <= seven_days,
            models.Action.status.in_(["Not Started", "In Progress"]),
            models.Action.is_deleted == False
        ).count()

        my_upcoming_hearings = db.query(models.Hearing).filter(
            models.Hearing.case_id.in_(my_case_ids),
            models.Hearing.hearing_date >= now,
            models.Hearing.hearing_date <= seven_days
        ).count()

        thirty_days_ago = now - timedelta(days=30)
        cases_without_updates = db.query(models.Case).filter(
            models.Case.id.in_(my_case_ids),
            models.Case.updated_at < thirty_days_ago,
            models.Case.status.notin_(["Closed", "Resolved"])
        ).count()

    my_unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    # State breakdown — as [name, total] pairs for Chart.js index access
    state_stats = [
        [r.name, r.total]
        for r in db.query(
            models.State.name,
            func.count(models.Case.id).label("total")
        ).join(models.Case, models.Case.state_id == models.State.id).filter(
            models.Case.is_deleted == False
        ).group_by(models.State.name).all()
    ]

    # Status breakdown — as [status, total] pairs
    status_stats = [
        [r.status, r.total]
        for r in db.query(
            models.Case.status,
            func.count(models.Case.id).label("total")
        ).filter(models.Case.is_deleted == False).group_by(models.Case.status).all()
    ]

    # Priority breakdown — as [priority, total] pairs
    priority_stats = [
        [r.priority, r.total]
        for r in db.query(
            models.Case.priority,
            func.count(models.Case.id).label("total")
        ).filter(models.Case.is_deleted == False).group_by(models.Case.priority).all()
    ]

    # Recent hearings
    recent_hearings = db.query(models.Hearing).join(models.Case).filter(
        models.Hearing.hearing_date >= now,
        models.Case.is_deleted == False
    ).order_by(models.Hearing.hearing_date).limit(5).all()

    # Recent actions overdue
    overdue_action_list = db.query(models.Action).join(models.Case).filter(
        models.Action.status == "Overdue",
        models.Action.is_deleted == False,
        models.Case.is_deleted == False
    ).order_by(models.Action.due_date).limit(5).all()

    # My recent notifications
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).order_by(models.Notification.created_at.desc()).limit(5).all()

    return templates.TemplateResponse(request, "dashboard.html", {
        "current_user": current_user,
        "total_cases": total_cases,
        "active_cases": active_cases,
        "new_cases": new_cases,
        "closed_cases": closed_cases,
        "critical_cases": critical_cases,
        "upcoming_hearings": upcoming_hearings,
        "overdue_actions": overdue_actions,
        "actions_due": actions_due,
        "my_cases_count": my_cases_count,
        "my_overdue": my_overdue,
        "my_due_soon": my_due_soon,
        "my_upcoming_hearings": my_upcoming_hearings,
        "my_unread_notifs": my_unread_notifs,
        "cases_without_updates": cases_without_updates,
        "state_stats": state_stats,
        "status_stats": status_stats,
        "priority_stats": priority_stats,
        "recent_hearings": recent_hearings,
        "overdue_action_list": overdue_action_list,
        "notifications": notifications,
        "now": now,
        "unread_notifs": my_unread_notifs,
    })
