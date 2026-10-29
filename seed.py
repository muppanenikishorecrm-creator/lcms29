"""Seed the database with initial data."""
from datetime import datetime, timedelta
import random
from database import SessionLocal, engine
import models
from auth import get_password_hash
from models import Base


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(models.User).count() > 0:
            print("Database already seeded.")
            return

        # States
        states_data = [
            ("Telangana", "TS"), ("Andhra Pradesh", "AP"), ("Maharashtra", "MH"),
            ("Karnataka", "KA"), ("Tamil Nadu", "TN"), ("Gujarat", "GJ"),
            ("Rajasthan", "RJ"), ("Delhi", "DL"),
        ]
        states = []
        for name, code in states_data:
            s = models.State(name=name, code=code)
            db.add(s)
            states.append(s)
        db.flush()

        # Districts
        districts_data = {
            "TS": ["Hyderabad", "Rangareddy", "Medchal", "Warangal", "Nizamabad"],
            "AP": ["Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Kurnool"],
            "MH": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad"],
        }
        districts = []
        state_map = {s.code: s for s in states}
        for code, dnames in districts_data.items():
            st = state_map.get(code)
            if st:
                for dname in dnames:
                    d = models.District(name=dname, state_id=st.id)
                    db.add(d)
                    districts.append(d)
        db.flush()

        # Courts
        court_types = ["High Court", "District Court", "Family Court", "Civil Court", "Criminal Court"]
        courts = []
        for district in districts[:6]:
            for ct in court_types[:2]:
                c = models.Court(name=f"{district.name} {ct}", court_type=ct, district_id=district.id)
                db.add(c)
                courts.append(c)
        db.flush()

        # Case Types
        case_type_names = [
            "PIL (Public Interest Litigation)", "Criminal Appeal", "Civil Suit",
            "Writ Petition", "Consumer Dispute", "Labour Dispute",
            "Property Dispute", "Family Matter", "Revenue Matter", "Constitutional Matter"
        ]
        case_types = []
        for ct_name in case_type_names:
            ct = models.CaseType(name=ct_name)
            db.add(ct)
            case_types.append(ct)
        db.flush()

        # Users
        ts_state = state_map["TS"]
        ap_state = state_map["AP"]

        users_data = [
            ("admin@lcms.in", "Admin User", "Admin@123", models.UserRole.org_admin, None),
            ("superadmin@lcms.in", "Super Admin", "Admin@123", models.UserRole.super_admin, None),
            ("ts.admin@lcms.in", "Telangana Admin", "Admin@123", models.UserRole.state_admin, ts_state.id),
            ("ap.admin@lcms.in", "AP Admin", "Admin@123", models.UserRole.state_admin, ap_state.id),
            ("cm1@lcms.in", "Priya Sharma", "Admin@123", models.UserRole.case_manager, ts_state.id),
            ("cm2@lcms.in", "Ravi Kumar", "Admin@123", models.UserRole.case_manager, ap_state.id),
            ("lawyer1@lcms.in", "Adv. Anil Reddy", "Admin@123", models.UserRole.lawyer, ts_state.id),
            ("lawyer2@lcms.in", "Adv. Sunita Patel", "Admin@123", models.UserRole.lawyer, ap_state.id),
            ("lawyer3@lcms.in", "Adv. Rajesh Nair", "Admin@123", models.UserRole.lawyer, ts_state.id),
            ("officer1@lcms.in", "Inspector Mehta", "Admin@123", models.UserRole.stakeholder, ts_state.id),
            ("officer2@lcms.in", "DSP Prasad", "Admin@123", models.UserRole.stakeholder, ap_state.id),
            ("viewer1@lcms.in", "Board Member", "Admin@123", models.UserRole.viewer, None),
        ]
        users = []
        for email, name, pwd, role, state_id in users_data:
            u = models.User(
                email=email,
                full_name=name,
                hashed_password=get_password_hash(pwd),
                role=role,
                state_id=state_id,
                is_active=True
            )
            db.add(u)
            users.append(u)
        db.flush()

        admin_user = users[0]
        cm1 = users[4]
        cm2 = users[5]
        lawyer1 = users[6]
        lawyer2 = users[7]
        lawyer3 = users[8]
        officer1 = users[9]

        # Cases
        petitioners = ["State of Telangana", "Ramesh Kumar", "XYZ Industries Ltd",
                       "Citizens Welfare Forum", "ABC Construction Co", "Municipal Corporation",
                       "Venkat Rao", "Lakshmi Devi", "National Highway Authority", "Union of India"]
        respondents = ["ABC Corporation", "State Government", "Ramaiah Holdings",
                       "District Collector", "HMDA", "Revenue Board",
                       "Police Department", "Land Records Dept", "PWD", "TSRTC"]

        statuses = list(models.CaseStatus)
        priorities = list(models.CasePriority)

        cases = []
        ts_courts = [c for c in courts if "Hyderabad" in c.name or "Rangareddy" in c.name]
        ap_courts = [c for c in courts if "Visakhapatnam" in c.name or "Vijayawada" in c.name]

        for i in range(1, 51):
            state = ts_state if i % 2 == 0 else ap_state
            state_code = "TS" if i % 2 == 0 else "AP"
            court_list = ts_courts if state == ts_state else ap_courts
            court = random.choice(court_list) if court_list else None
            district_id = court.district_id if court else None

            case_id = f"LCMS-{state_code}-2026-{i:06d}"
            status_val = random.choice(statuses).value
            priority_val = random.choice(priorities).value
            case_type = random.choice(case_types)

            days_ago = random.randint(1, 365)
            created_date = datetime.now() - timedelta(days=days_ago)
            next_hearing = datetime.now() + timedelta(days=random.randint(-10, 60))

            petitioner = random.choice(petitioners)
            respondent = random.choice(respondents)

            case = models.Case(
                case_id=case_id,
                title=f"{petitioner} vs {respondent}",
                case_type_id=case_type.id,
                category=random.choice(["Civil", "Criminal", "Constitutional", "Revenue", "Labour"]),
                priority=priority_val,
                status=status_val,
                description=f"Legal matter filed by {petitioner} against {respondent}.",
                state_id=state.id,
                district_id=district_id,
                court_id=court.id if court else None,
                city=random.choice(["Hyderabad", "Secunderabad", "Vijayawada", "Visakhapatnam"]),
                case_number=f"WP/{1000+i}/{2026 - random.randint(0,3)}",
                cnr_number=f"TS{random.randint(100000,999999)}2026",
                applicable_act="Constitution of India",
                sections=random.choice(["Article 226", "Section 482 CrPC", "Article 32", "Section 34 IPC"]),
                date_filed=created_date,
                date_received=created_date - timedelta(days=random.randint(1, 30)),
                next_hearing_date=next_hearing if status_val not in ["Closed", "Resolved"] else None,
                created_at=created_date,
            )
            db.add(case)
            cases.append(case)
        db.flush()

        # Assignments
        for case in cases:
            lawyer = random.choice([lawyer1, lawyer2, lawyer3])
            cm = random.choice([cm1, cm2])

            db.add(models.CaseAssignment(case_id=case.id, user_id=lawyer.id, role="primary_lawyer"))
            db.add(models.CaseAssignment(case_id=case.id, user_id=cm.id, role="case_manager"))
            if random.random() > 0.5:
                db.add(models.CaseAssignment(case_id=case.id, user_id=officer1.id, role="stakeholder"))
        db.flush()

        # Parties
        for case in cases:
            title_parts = case.title.split(" vs ")
            pet_name = title_parts[0] if len(title_parts) > 0 else "Petitioner"
            res_name = title_parts[1] if len(title_parts) > 1 else "Respondent"
            db.add(models.CaseParty(case_id=case.id, party_type="Petitioner", name=pet_name))
            db.add(models.CaseParty(case_id=case.id, party_type="Respondent", name=res_name))
        db.flush()

        # Hearings
        hearing_types = ["First Hearing", "Arguments", "Evidence", "Final Arguments", "Order", "Compliance"]
        for case in cases[:30]:
            n_hearings = random.randint(1, 4)
            base_date = case.date_filed or (datetime.now() - timedelta(days=200))
            for j in range(n_hearings):
                h_date = base_date + timedelta(days=30 * (j + 1))
                next_h = h_date + timedelta(days=random.randint(15, 45))
                h = models.Hearing(
                    case_id=case.id,
                    court_id=case.court_id,
                    hearing_date=h_date,
                    hearing_type=random.choice(hearing_types),
                    purpose=f"Hearing #{j+1}",
                    outcome=random.choice(["Adjourned", "Part heard", "Arguments completed", "Order reserved"]),
                    next_hearing_date=next_h if j < n_hearings - 1 else None,
                    notes=f"Proceeding notes for hearing {j+1}",
                    created_by_id=admin_user.id,
                )
                db.add(h)
        db.flush()

        # Actions
        action_titles = [
            "File compliance report", "Submit affidavit", "Serve notice to respondent",
            "Obtain certified copies", "File counter affidavit", "Prepare written arguments",
            "Coordinate with police station", "Submit documents to court",
            "Follow up with lawyer", "Update case status"
        ]
        action_counter = 1
        for case in cases:
            n_actions = random.randint(1, 4)
            for k in range(n_actions):
                due_days = random.randint(-15, 45)
                due = datetime.now() + timedelta(days=due_days)
                status_val = models.ActionStatus.not_started.value
                if due_days < -7:
                    status_val = random.choice([models.ActionStatus.overdue.value, models.ActionStatus.completed.value])
                elif due_days < 0:
                    status_val = random.choice([models.ActionStatus.in_progress.value, models.ActionStatus.overdue.value])
                elif due_days < 5:
                    status_val = models.ActionStatus.in_progress.value

                a = models.Action(
                    action_id=f"ACT-{action_counter:05d}",
                    case_id=case.id,
                    title=random.choice(action_titles),
                    description="Action required to advance the case.",
                    assigned_to_id=random.choice([lawyer1, lawyer2, cm1, officer1]).id,
                    created_by_id=cm1.id,
                    priority=random.choice(priorities).value,
                    due_date=due,
                    status=status_val,
                )
                db.add(a)
                action_counter += 1
        db.flush()

        # Timeline entries
        for case in cases[:20]:
            db.add(models.CaseTimeline(
                case_id=case.id,
                event="Case Created",
                description="Case was registered in the system.",
                user_id=cm1.id,
                new_status=models.CaseStatus.new.value,
                created_at=case.date_filed or datetime.now() - timedelta(days=100),
            ))
            db.add(models.CaseTimeline(
                case_id=case.id,
                event="Status Updated",
                description="Case moved to Active.",
                user_id=admin_user.id,
                prev_status=models.CaseStatus.new.value,
                new_status=models.CaseStatus.active.value,
                created_at=(case.date_filed or datetime.now() - timedelta(days=100)) + timedelta(days=7),
            ))
        db.flush()

        # Notifications
        notif_data = [
            (cm1.id, cases[0].id, "Action Due Tomorrow", "File compliance report is due tomorrow.", "urgent"),
            (lawyer1.id, cases[1].id, "Hearing Scheduled", "Hearing on 20 Feb 2026 at 10:30 AM.", "info"),
            (cm1.id, cases[2].id, "Action Overdue", "Submit affidavit is 3 days overdue.", "warning"),
            (admin_user.id, cases[3].id, "Critical Case Update", "Case escalated to critical priority.", "escalation"),
            (lawyer2.id, cases[4].id, "Document Uploaded", "New order uploaded for your case.", "info"),
            (cm2.id, cases[5].id, "Action Due in 3 Days", "Serve notice to respondent is due in 3 days.", "warning"),
        ]
        for uid, cid, title, msg, ntype in notif_data:
            db.add(models.Notification(
                user_id=uid, case_id=cid, title=title, message=msg, type=ntype
            ))

        # Notes
        for case in cases[:15]:
            db.add(models.CaseNote(
                case_id=case.id,
                content=f"Initial review completed. Case {case.case_id} has been assigned and is under progress.",
                created_by_id=cm1.id,
            ))

        db.commit()
        print("✅ Database seeded successfully!")
        print("\nDemo credentials:")
        print("  Super Admin:   superadmin@lcms.in / Admin@123")
        print("  Org Admin:     admin@lcms.in / Admin@123")
        print("  State Admin:   ts.admin@lcms.in / Admin@123")
        print("  Case Manager:  cm1@lcms.in / Admin@123")
        print("  Lawyer:        lawyer1@lcms.in / Admin@123")
        print("  Stakeholder:   officer1@lcms.in / Admin@123")
        print("  Viewer:        viewer1@lcms.in / Admin@123")

    except Exception as e:
        db.rollback()
        print(f"Error seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
