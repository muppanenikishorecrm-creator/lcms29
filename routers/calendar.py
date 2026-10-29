from templates_config import templates
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from database import get_db
from auth import require_user
import models
from datetime import datetime, timedelta
import calendar as cal
import json

router = APIRouter()

@router.get("/calendar", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    year: int = Query(None),
    month: int = Query(None),
):
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month

    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    hearings = db.query(models.Hearing).join(models.Case).options(
        joinedload(models.Hearing.case)
    ).filter(
        models.Hearing.hearing_date >= first_day,
        models.Hearing.hearing_date <= last_day,
        models.Case.is_deleted == False
    ).all()

    actions = db.query(models.Action).join(models.Case).options(
        joinedload(models.Action.case)
    ).filter(
        models.Action.due_date >= first_day,
        models.Action.due_date <= last_day,
        models.Case.is_deleted == False,
        models.Action.is_deleted == False
    ).all()

    # Build events dict by day
    events = {}
    for h in hearings:
        day = h.hearing_date.day
        if day not in events:
            events[day] = []
        events[day].append({"type": "hearing", "title": h.case.title[:30], "case_id": h.case.id, "detail": h.hearing_type or "Hearing"})

    for a in actions:
        day = a.due_date.day
        if day not in events:
            events[day] = []
        events[day].append({"type": "action", "title": a.title[:30], "case_id": a.case_id, "detail": a.status, "overdue": a.status == "Overdue"})

    # Build calendar weeks
    weeks = cal.monthcalendar(year, month)

    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    return templates.TemplateResponse(request, "calendar.html", {
        "current_user": current_user,
        "year": year,
        "month": month,
        "month_name": first_day.strftime("%B %Y"),
        "weeks": weeks,
        "events": events,
        "prev_month": prev_month,
        "prev_year": prev_year,
        "next_month": next_month,
        "next_year": next_year,
        "today": now.day if now.year == year and now.month == month else -1,
        "unread_notifs": unread_notifs,
    })
