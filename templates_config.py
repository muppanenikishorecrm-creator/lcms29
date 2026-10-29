from fastapi.templating import Jinja2Templates
from datetime import datetime
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def format_date(value, fmt="%d %b %Y"):
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return value
    return value.strftime(fmt)


def days_from_now(value):
    if not value:
        return None
    now = datetime.utcnow()
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except Exception:
            return None
    return (value - now).days


def status_color(status):
    colors = {
        "New": "blue", "Under Review": "indigo", "Active": "green",
        "Hearing / Action Pending": "yellow", "Awaiting Order": "orange",
        "Order Received": "teal", "Compliance / Follow-up": "purple",
        "Resolved": "emerald", "Closed": "gray", "On Hold": "yellow",
        "Withdrawn": "gray", "Transferred": "gray", "Settled": "emerald",
        "Dismissed": "red", "Appealed": "orange",
    }
    return colors.get(status, "gray")


def priority_color(priority):
    return {"Low": "gray", "Medium": "blue", "High": "orange", "Critical": "red"}.get(priority, "gray")


def action_status_color(status):
    return {
        "Not Started": "gray", "In Progress": "blue", "Completed": "green",
        "Cancelled": "gray", "Overdue": "red",
    }.get(status, "gray")


def role_label(role):
    return {
        "super_admin": "Super Admin", "org_admin": "Org Admin",
        "state_admin": "State Admin", "case_manager": "Case Manager",
        "lawyer": "Lawyer", "stakeholder": "Stakeholder", "viewer": "Viewer",
    }.get(role, role)


templates.env.filters["format_date"] = format_date
templates.env.filters["days_from_now"] = days_from_now
templates.env.filters["status_color"] = status_color
templates.env.filters["priority_color"] = priority_color
templates.env.filters["action_status_color"] = action_status_color
templates.env.filters["role_label"] = role_label
templates.env.globals["now"] = datetime.utcnow
