from templates_config import templates
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from auth import require_user
import models
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/reports", response_class=HTMLResponse)
async def reports(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    report_type: str = Query("overview"),
):
    now = datetime.utcnow()

    # State-wise report
    from sqlalchemy import Integer as SAInteger, cast, case as sa_case
    state_report = db.query(
        models.State.name.label("state"),
        func.count(models.Case.id).label("total"),
        func.sum(sa_case((models.Case.status.in_(["Active","Hearing / Action Pending","Awaiting Order","Order Received","Compliance / Follow-up"]), 1), else_=0)).label("active"),
        func.sum(sa_case((models.Case.status.in_(["Closed","Resolved"]), 1), else_=0)).label("closed"),
        func.sum(sa_case((models.Case.priority == "Critical", 1), else_=0)).label("critical"),
    ).join(models.Case, models.Case.state_id == models.State.id).filter(
        models.Case.is_deleted == False
    ).group_by(models.State.name).all()

    # Lawyer performance
    lawyer_report = db.query(
        models.User.full_name.label("lawyer"),
        func.count(models.CaseAssignment.id).label("total_cases"),
    ).join(models.CaseAssignment, models.CaseAssignment.user_id == models.User.id).filter(
        models.User.role == "lawyer",
        models.CaseAssignment.role == "primary_lawyer",
        models.CaseAssignment.is_active == True
    ).group_by(models.User.full_name).all()

    # Case ageing
    ageing = {
        "0-30 days": db.query(func.count(models.Case.id)).filter(
            models.Case.is_deleted == False,
            models.Case.date_filed >= now - timedelta(days=30)
        ).scalar() or 0,
        "31-90 days": db.query(func.count(models.Case.id)).filter(
            models.Case.is_deleted == False,
            models.Case.date_filed >= now - timedelta(days=90),
            models.Case.date_filed < now - timedelta(days=30)
        ).scalar() or 0,
        "91-180 days": db.query(func.count(models.Case.id)).filter(
            models.Case.is_deleted == False,
            models.Case.date_filed >= now - timedelta(days=180),
            models.Case.date_filed < now - timedelta(days=90)
        ).scalar() or 0,
        "181-365 days": db.query(func.count(models.Case.id)).filter(
            models.Case.is_deleted == False,
            models.Case.date_filed >= now - timedelta(days=365),
            models.Case.date_filed < now - timedelta(days=180)
        ).scalar() or 0,
        "1-2 years": db.query(func.count(models.Case.id)).filter(
            models.Case.is_deleted == False,
            models.Case.date_filed >= now - timedelta(days=730),
            models.Case.date_filed < now - timedelta(days=365)
        ).scalar() or 0,
        "2+ years": db.query(func.count(models.Case.id)).filter(
            models.Case.is_deleted == False,
            models.Case.date_filed < now - timedelta(days=730)
        ).scalar() or 0,
    }

    # Outcome report
    outcome_report = db.query(
        models.Case.outcome,
        func.count(models.Case.id).label("total")
    ).filter(
        models.Case.is_deleted == False,
        models.Case.outcome != None
    ).group_by(models.Case.outcome).all()

    # Priority distribution
    priority_report = db.query(
        models.Case.priority,
        func.count(models.Case.id).label("total")
    ).filter(models.Case.is_deleted == False).group_by(models.Case.priority).all()

    # Action stats
    action_stats = {
        "total": db.query(func.count(models.Action.id)).filter(models.Action.is_deleted == False).scalar() or 0,
        "completed": db.query(func.count(models.Action.id)).filter(models.Action.status == "Completed", models.Action.is_deleted == False).scalar() or 0,
        "overdue": db.query(func.count(models.Action.id)).filter(models.Action.status == "Overdue", models.Action.is_deleted == False).scalar() or 0,
        "pending": db.query(func.count(models.Action.id)).filter(models.Action.status.in_(["Not Started", "In Progress"]), models.Action.is_deleted == False).scalar() or 0,
    }

    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    return templates.TemplateResponse(request, "reports.html", {
        "current_user": current_user,
        "state_report": state_report,
        "lawyer_report": lawyer_report,
        "ageing": ageing,
        "outcome_report": outcome_report,
        "priority_report": priority_report,
        "action_stats": action_stats,
        "report_type": report_type,
        "unread_notifs": unread_notifs,
    })


@router.get("/audit-logs", response_class=HTMLResponse)
async def audit_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc()).limit(200).all()
    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    return templates.TemplateResponse(request, "audit_logs.html", {
        "current_user": current_user,
        "logs": logs,
        "unread_notifs": unread_notifs,
    })
