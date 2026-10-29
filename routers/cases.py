from templates_config import templates
from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from database import get_db
from auth import require_user
import models
from datetime import datetime
import random
import string

router = APIRouter()

def gen_case_id(state_code: str) -> str:
    year = datetime.now().year
    suffix = ''.join(random.choices(string.digits, k=6))
    return f"LCMS-{state_code}-{year}-{suffix}"


def add_timeline(db, case_id, event, desc, user_id, prev_status=None, new_status=None):
    entry = models.CaseTimeline(
        case_id=case_id, event=event, description=desc,
        user_id=user_id, prev_status=prev_status, new_status=new_status
    )
    db.add(entry)


def add_audit(db, user_id, case_id, action, entity_type=None, entity_id=None, details=None):
    log = models.AuditLog(
        user_id=user_id, case_id=case_id, action=action,
        entity_type=entity_type, entity_id=entity_id, details=details
    )
    db.add(log)


@router.get("/cases", response_class=HTMLResponse)
async def case_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    search: str = Query(""),
    status: str = Query(""),
    priority: str = Query(""),
    state_id: int = Query(None),
    case_type_id: int = Query(None),
    page: int = Query(1),
):
    per_page = 20
    q = db.query(models.Case).filter(models.Case.is_deleted == False)

    if search:
        q = q.filter(or_(
            models.Case.title.ilike(f"%{search}%"),
            models.Case.case_id.ilike(f"%{search}%"),
            models.Case.case_number.ilike(f"%{search}%"),
            models.Case.cnr_number.ilike(f"%{search}%"),
        ))
    if status:
        q = q.filter(models.Case.status == status)
    if priority:
        q = q.filter(models.Case.priority == priority)
    if state_id:
        q = q.filter(models.Case.state_id == state_id)
    if case_type_id:
        q = q.filter(models.Case.case_type_id == case_type_id)

    # Role-based filtering
    if current_user.role == "state_admin" and current_user.state_id:
        q = q.filter(models.Case.state_id == current_user.state_id)
    elif current_user.role in ["lawyer", "case_manager", "stakeholder"]:
        assigned = db.query(models.CaseAssignment.case_id).filter(
            models.CaseAssignment.user_id == current_user.id
        ).subquery()
        q = q.filter(models.Case.id.in_(assigned))

    total = q.count()
    cases = q.options(
        joinedload(models.Case.state),
        joinedload(models.Case.court),
        joinedload(models.Case.case_type_rel)
    ).order_by(models.Case.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    states = db.query(models.State).filter(models.State.is_active == True).all()
    case_types = db.query(models.CaseType).filter(models.CaseType.is_active == True).all()
    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    return templates.TemplateResponse(request, "cases/list.html", {
        "current_user": current_user,
        "cases": cases,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "search": search,
        "status_filter": status,
        "priority_filter": priority,
        "state_filter": state_id,
        "states": states,
        "case_types": case_types,
        "statuses": [s.value for s in models.CaseStatus],
        "priorities": [p.value for p in models.CasePriority],
        "unread_notifs": unread_notifs,
    })


@router.get("/cases/create", response_class=HTMLResponse)
async def create_case_form(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(require_user)):
    states = db.query(models.State).filter(models.State.is_active == True).all()
    case_types = db.query(models.CaseType).filter(models.CaseType.is_active == True).all()
    users = db.query(models.User).filter(models.User.is_active == True).all()
    courts = db.query(models.Court).all()
    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()
    return templates.TemplateResponse(request, "cases/create.html", {
        "current_user": current_user,
        "states": states,
        "case_types": case_types,
        "users": users,
        "courts": courts,
        "priorities": [p.value for p in models.CasePriority],
        "unread_notifs": unread_notifs,
    })


@router.post("/cases/create")
async def create_case(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    title: str = Form(...),
    case_type_id: int = Form(None),
    category: str = Form(""),
    priority: str = Form("Medium"),
    description: str = Form(""),
    state_id: int = Form(None),
    district_id: int = Form(None),
    city: str = Form(""),
    court_id: int = Form(None),
    case_number: str = Form(""),
    cnr_number: str = Form(""),
    fir_number: str = Form(""),
    applicable_act: str = Form(""),
    sections: str = Form(""),
    date_filed: str = Form(""),
    petitioner_name: str = Form(""),
    respondent_name: str = Form(""),
    lawyer_id: int = Form(None),
    case_manager_id: int = Form(None),
    stakeholder_id: int = Form(None),
):
    state = db.query(models.State).filter(models.State.id == state_id).first() if state_id else None
    state_code = state.code if state else "XX"
    case_id = gen_case_id(state_code)

    filed_date = None
    if date_filed:
        try:
            filed_date = datetime.strptime(date_filed, "%Y-%m-%d")
        except ValueError:
            pass

    case = models.Case(
        case_id=case_id,
        title=title,
        case_type_id=case_type_id,
        category=category,
        priority=priority,
        description=description,
        status=models.CaseStatus.new.value,
        state_id=state_id,
        district_id=district_id,
        city=city,
        court_id=court_id,
        case_number=case_number,
        cnr_number=cnr_number,
        fir_number=fir_number,
        applicable_act=applicable_act,
        sections=sections,
        date_filed=filed_date,
    )
    db.add(case)
    db.flush()

    if petitioner_name:
        db.add(models.CaseParty(case_id=case.id, party_type="Petitioner", name=petitioner_name))
    if respondent_name:
        db.add(models.CaseParty(case_id=case.id, party_type="Respondent", name=respondent_name))

    if lawyer_id:
        db.add(models.CaseAssignment(case_id=case.id, user_id=lawyer_id, role="primary_lawyer"))
    if case_manager_id:
        db.add(models.CaseAssignment(case_id=case.id, user_id=case_manager_id, role="case_manager"))
    if stakeholder_id:
        db.add(models.CaseAssignment(case_id=case.id, user_id=stakeholder_id, role="stakeholder"))

    add_timeline(db, case.id, "Case Created", f"Case {case_id} created.", current_user.id, new_status=models.CaseStatus.new.value)
    add_audit(db, current_user.id, case.id, "CREATE_CASE", "Case", case.id, f"Created case {case_id}")

    db.commit()
    return RedirectResponse(url=f"/cases/{case.id}", status_code=302)


@router.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_detail(
    request: Request,
    case_id: int,
    tab: str = Query("overview"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    case = db.query(models.Case).options(
        joinedload(models.Case.state),
        joinedload(models.Case.district),
        joinedload(models.Case.court),
        joinedload(models.Case.case_type_rel),
        joinedload(models.Case.parties),
        joinedload(models.Case.assignments).joinedload(models.CaseAssignment.user),
        joinedload(models.Case.hearings),
        joinedload(models.Case.actions).joinedload(models.Action.assigned_to_user),
        joinedload(models.Case.documents).joinedload(models.Document.uploaded_by_user),
        joinedload(models.Case.notes).joinedload(models.CaseNote.created_by),
        joinedload(models.Case.timeline).joinedload(models.CaseTimeline.user),
    ).filter(models.Case.id == case_id, models.Case.is_deleted == False).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    users = db.query(models.User).filter(models.User.is_active == True).all()
    courts = db.query(models.Court).all()
    states = db.query(models.State).all()
    unread_notifs = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False
    ).count()

    # Sort timeline descending
    timeline = sorted(case.timeline, key=lambda x: x.created_at, reverse=True)
    hearings = sorted(case.hearings, key=lambda x: x.hearing_date, reverse=True)
    actions = [a for a in case.actions if not a.is_deleted]
    documents = [d for d in case.documents if not d.is_deleted]

    return templates.TemplateResponse(request, "cases/detail.html", {
        "current_user": current_user,
        "case": case,
        "timeline": timeline,
        "hearings": hearings,
        "actions": actions,
        "documents": documents,
        "users": users,
        "courts": courts,
        "states": states,
        "tab": tab,
        "statuses": [s.value for s in models.CaseStatus],
        "priorities": [p.value for p in models.CasePriority],
        "outcomes": [o.value for o in models.CaseOutcome],
        "action_statuses": [a.value for a in models.ActionStatus],
        "unread_notifs": unread_notifs,
        "now": datetime.utcnow(),
    })


@router.post("/cases/{case_id}/update-status")
async def update_case_status(
    case_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user)
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404)
    prev = case.status
    case.status = status
    add_timeline(db, case.id, "Status Updated", f"Status changed from {prev} to {status}", current_user.id, prev, status)
    add_audit(db, current_user.id, case.id, "UPDATE_STATUS", "Case", case.id, f"{prev} → {status}")
    db.commit()
    return RedirectResponse(url=f"/cases/{case_id}?tab=overview", status_code=302)


@router.post("/cases/{case_id}/add-hearing")
async def add_hearing(
    case_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    hearing_date: str = Form(...),
    hearing_type: str = Form(""),
    purpose: str = Form(""),
    bench: str = Form(""),
    lawyer_attending: str = Form(""),
    outcome: str = Form(""),
    next_hearing_date: str = Form(""),
    notes: str = Form(""),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404)

    hdate = datetime.strptime(hearing_date, "%Y-%m-%d") if hearing_date else None
    nhdate = datetime.strptime(next_hearing_date, "%Y-%m-%d") if next_hearing_date else None

    h = models.Hearing(
        case_id=case_id,
        court_id=case.court_id,
        hearing_date=hdate,
        hearing_type=hearing_type,
        purpose=purpose,
        bench=bench,
        lawyer_attending=lawyer_attending,
        outcome=outcome,
        next_hearing_date=nhdate,
        notes=notes,
        created_by_id=current_user.id,
    )
    db.add(h)

    if nhdate:
        case.next_hearing_date = nhdate

    add_timeline(db, case_id, "Hearing Added", f"Hearing on {hearing_date}. Outcome: {outcome}", current_user.id)
    add_audit(db, current_user.id, case_id, "ADD_HEARING", "Hearing", None, f"Hearing on {hearing_date}")
    db.commit()
    return RedirectResponse(url=f"/cases/{case_id}?tab=hearings", status_code=302)


@router.post("/cases/{case_id}/add-action")
async def add_action(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
    title: str = Form(...),
    description: str = Form(""),
    assigned_to_id: int = Form(None),
    priority: str = Form("Medium"),
    due_date: str = Form(""),
):
    ddate = datetime.strptime(due_date, "%Y-%m-%d") if due_date else None
    suffix = ''.join(random.choices(string.digits, k=5))
    action = models.Action(
        action_id=f"ACT-{suffix}",
        case_id=case_id,
        title=title,
        description=description,
        assigned_to_id=assigned_to_id,
        created_by_id=current_user.id,
        priority=priority,
        due_date=ddate,
        status=models.ActionStatus.not_started.value,
    )
    db.add(action)
    add_timeline(db, case_id, "Action Created", f"Action: {title}", current_user.id)
    add_audit(db, current_user.id, case_id, "ADD_ACTION", "Action", None, title)
    db.commit()
    return RedirectResponse(url=f"/cases/{case_id}?tab=actions", status_code=302)


@router.post("/cases/{case_id}/add-note")
async def add_note(
    case_id: int,
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    note = models.CaseNote(case_id=case_id, content=content, created_by_id=current_user.id)
    db.add(note)
    add_timeline(db, case_id, "Note Added", content[:80], current_user.id)
    db.commit()
    return RedirectResponse(url=f"/cases/{case_id}?tab=notes", status_code=302)


@router.post("/cases/{case_id}/set-outcome")
async def set_outcome(
    case_id: int,
    outcome: str = Form(...),
    outcome_date: str = Form(""),
    outcome_notes: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_user),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404)
    odate = datetime.strptime(outcome_date, "%Y-%m-%d") if outcome_date else None
    case.outcome = outcome
    case.outcome_date = odate
    case.outcome_notes = outcome_notes
    case.status = models.CaseStatus.closed.value
    add_timeline(db, case_id, "Outcome Recorded", f"Outcome: {outcome}", current_user.id, case.status, models.CaseStatus.closed.value)
    add_audit(db, current_user.id, case_id, "SET_OUTCOME", "Case", case_id, f"Outcome: {outcome}")
    db.commit()
    return RedirectResponse(url=f"/cases/{case_id}?tab=outcome", status_code=302)
