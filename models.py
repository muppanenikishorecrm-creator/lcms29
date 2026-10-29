from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    org_admin = "org_admin"
    state_admin = "state_admin"
    case_manager = "case_manager"
    lawyer = "lawyer"
    stakeholder = "stakeholder"
    viewer = "viewer"


class CaseStatus(str, enum.Enum):
    new = "New"
    under_review = "Under Review"
    active = "Active"
    hearing_pending = "Hearing / Action Pending"
    awaiting_order = "Awaiting Order"
    order_received = "Order Received"
    compliance = "Compliance / Follow-up"
    resolved = "Resolved"
    closed = "Closed"
    on_hold = "On Hold"
    withdrawn = "Withdrawn"
    transferred = "Transferred"
    settled = "Settled"
    dismissed = "Dismissed"
    appealed = "Appealed"


class CasePriority(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"


class ActionStatus(str, enum.Enum):
    not_started = "Not Started"
    in_progress = "In Progress"
    completed = "Completed"
    cancelled = "Cancelled"
    overdue = "Overdue"


class CaseOutcome(str, enum.Enum):
    favourable = "Favourable"
    partially_favourable = "Partially Favourable"
    unfavourable = "Unfavourable"
    settled = "Settled"
    withdrawn = "Withdrawn"
    dismissed = "Dismissed"
    transferred = "Transferred"
    pending = "Pending at Closure"
    other = "Other"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.case_manager)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    phone = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    state = relationship("State", back_populates="users")
    assigned_cases = relationship("CaseAssignment", back_populates="user")
    actions = relationship("Action", back_populates="assigned_to_user", foreign_keys="Action.assigned_to_id")
    created_actions = relationship("Action", back_populates="created_by_user", foreign_keys="Action.created_by_id")
    uploaded_documents = relationship("Document", back_populates="uploaded_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="state")
    districts = relationship("District", back_populates="state")
    cases = relationship("Case", back_populates="state")


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    state = relationship("State", back_populates="districts")
    courts = relationship("Court", back_populates="district")
    cases = relationship("Case", back_populates="district")


class Court(Base):
    __tablename__ = "courts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    court_type = Column(String, nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    district = relationship("District", back_populates="courts")
    cases = relationship("Case", back_populates="court")
    hearings = relationship("Hearing", back_populates="court")


class CaseType(Base):
    __tablename__ = "case_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    cases = relationship("Case", back_populates="case_type_rel")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True, nullable=False)
    internal_ref = Column(String, nullable=True)
    title = Column(String, nullable=False)
    case_type_id = Column(Integer, ForeignKey("case_types.id"), nullable=True)
    category = Column(String, nullable=True)
    priority = Column(String, default=CasePriority.medium)
    confidentiality = Column(String, default="Normal")
    description = Column(Text, nullable=True)
    status = Column(String, default=CaseStatus.new)

    # Jurisdiction
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    city = Column(String, nullable=True)
    court_id = Column(Integer, ForeignKey("courts.id"), nullable=True)
    police_station = Column(String, nullable=True)
    authority = Column(String, nullable=True)

    # Legal info
    case_number = Column(String, nullable=True)
    filing_number = Column(String, nullable=True)
    cnr_number = Column(String, nullable=True)
    fir_number = Column(String, nullable=True)
    applicable_act = Column(String, nullable=True)
    sections = Column(Text, nullable=True)
    petition_type = Column(String, nullable=True)

    # Dates
    date_received = Column(DateTime, nullable=True)
    date_filed = Column(DateTime, nullable=True)
    next_hearing_date = Column(DateTime, nullable=True)

    # Outcome
    outcome = Column(String, nullable=True)
    outcome_date = Column(DateTime, nullable=True)
    outcome_notes = Column(Text, nullable=True)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    state = relationship("State", back_populates="cases")
    district = relationship("District", back_populates="cases")
    court = relationship("Court", back_populates="cases")
    case_type_rel = relationship("CaseType", back_populates="cases")
    parties = relationship("CaseParty", back_populates="case", cascade="all, delete-orphan")
    assignments = relationship("CaseAssignment", back_populates="case", cascade="all, delete-orphan")
    hearings = relationship("Hearing", back_populates="case", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")
    timeline = relationship("CaseTimeline", back_populates="case", cascade="all, delete-orphan", order_by="CaseTimeline.created_at.desc()")
    audit_logs = relationship("AuditLog", back_populates="case")


class CaseParty(Base):
    __tablename__ = "case_parties"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    party_type = Column(String, nullable=False)  # Petitioner, Respondent, Other
    name = Column(String, nullable=False)
    contact = Column(String, nullable=True)
    address = Column(Text, nullable=True)

    case = relationship("Case", back_populates="parties")


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # primary_lawyer, supporting_lawyer, case_manager, stakeholder
    is_active = Column(Boolean, default=True)
    assigned_at = Column(DateTime, server_default=func.now())

    case = relationship("Case", back_populates="assignments")
    user = relationship("User", back_populates="assigned_cases")


class Hearing(Base):
    __tablename__ = "hearings"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    court_id = Column(Integer, ForeignKey("courts.id"), nullable=True)
    hearing_date = Column(DateTime, nullable=False)
    hearing_type = Column(String, nullable=True)
    purpose = Column(String, nullable=True)
    bench = Column(String, nullable=True)
    lawyer_attending = Column(String, nullable=True)
    stakeholder_attending = Column(String, nullable=True)
    outcome = Column(Text, nullable=True)
    next_hearing_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    order_available = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    case = relationship("Case", back_populates="hearings")
    court = relationship("Court", back_populates="hearings")


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(String, unique=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    priority = Column(String, default=CasePriority.medium)
    start_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default=ActionStatus.not_started)
    completion_date = Column(DateTime, nullable=True)
    completion_notes = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    case = relationship("Case", back_populates="actions")
    assigned_to_user = relationship("User", back_populates="actions", foreign_keys=[assigned_to_id])
    created_by_user = relationship("User", back_populates="created_actions", foreign_keys=[created_by_id])


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    name = Column(String, nullable=False)
    doc_type = Column(String, nullable=True)
    doc_date = Column(DateTime, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    confidentiality = Column(String, default="Normal")
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    case = relationship("Case", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="uploaded_documents")


class CaseNote(Base):
    __tablename__ = "case_notes"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_confidential = Column(Boolean, default=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    case = relationship("Case", back_populates="notes")
    created_by = relationship("User")


class CaseTimeline(Base):
    __tablename__ = "case_timeline"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    event = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    prev_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    case = relationship("Case", back_populates="timeline")
    user = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info")  # info, warning, urgent, escalation
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")
    case = relationship("Case")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="audit_logs")
    case = relationship("Case", back_populates="audit_logs")
