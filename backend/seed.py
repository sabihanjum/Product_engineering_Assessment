from app.main import Base, SessionLocal, User, Ticket, Activity, Role, Category, Priority, TicketStatus, engine, pwd_context
from datetime import datetime, timedelta, timezone

Base.metadata.create_all(bind=engine)
db = SessionLocal()
if not db.query(User).first():
    student = User(name="Aisha Khan", email="student@edusupport.demo", password_hash=pwd_context.hash("demo123"), role=Role.STUDENT)
    staff = User(name="Rahul Mehta", email="staff@edusupport.demo", password_hash=pwd_context.hash("demo123"), role=Role.STAFF)
    manager = User(name="Priya Shah", email="manager@edusupport.demo", password_hash=pwd_context.hash("demo123"), role=Role.MANAGER)
    db.add_all([student, staff, manager])
    db.flush()
    now = datetime.now(timezone.utc)
    tickets = [
        Ticket(subject="Semester fee payment still pending", description="I paid yesterday but the student portal still shows pending.", category=Category.FEES, priority=Priority.HIGH, status=TicketStatus.IN_PROGRESS, student_id=student.id, assigned_to_id=staff.id, due_at=now + timedelta(hours=2)),
        Ticket(subject="Request enrollment certificate", description="I need an enrollment certificate for a scholarship application.", category=Category.CERTIFICATE, priority=Priority.MEDIUM, status=TicketStatus.OPEN, student_id=student.id, due_at=now + timedelta(hours=10)),
        Ticket(subject="ID card replacement", description="My ID card was lost and I need a replacement.", category=Category.ID_CARD, priority=Priority.URGENT, status=TicketStatus.RESOLVED, student_id=student.id, assigned_to_id=staff.id, due_at=now - timedelta(hours=4), resolved_at=now - timedelta(hours=1)),
    ]
    db.add_all(tickets)
    db.flush()
    db.add_all([Activity(ticket_id=tickets[0].id, actor_id=student.id, action="Ticket created"), Activity(ticket_id=tickets[0].id, actor_id=staff.id, action="Assigned to Rahul Mehta"), Activity(ticket_id=tickets[0].id, actor_id=staff.id, action="Status changed: ASSIGNED -> IN_PROGRESS")])
    db.commit()
db.close()