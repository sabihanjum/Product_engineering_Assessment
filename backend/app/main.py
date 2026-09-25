from datetime import datetime, timedelta, timezone
from enum import Enum
import os
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edusupport.db")
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class Base(DeclarativeBase):
    pass


class Role(str, Enum):
    STUDENT = "STUDENT"
    STAFF = "STAFF"
    MANAGER = "MANAGER"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_STUDENT = "PENDING_STUDENT"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Category(str, Enum):
    FEES = "Fees"
    ATTENDANCE = "Attendance"
    ID_CARD = "ID Card"
    CERTIFICATE = "Certificate"
    DOCUMENTS = "Documents"
    EXAMINATION = "Examination"
    HOSTEL = "Hostel"
    TRANSPORT = "Transport"
    TECHNICAL = "Technical"
    OTHER = "Other"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SqlEnum(Role))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[Category] = mapped_column(SqlEnum(Category))
    priority: Mapped[Priority] = mapped_column(SqlEnum(Priority), default=Priority.MEDIUM)
    status: Mapped[TicketStatus] = mapped_column(SqlEnum(TicketStatus), default=TicketStatus.OPEN)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_to_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Comment(Base):
    __tablename__ = "ticket_comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Activity(Base):
    __tablename__ = "ticket_activity"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=6)
    role: Role = Role.STUDENT


class TicketCreate(BaseModel):
    subject: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=10)
    category: Category
    priority: Priority = Priority.MEDIUM


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[Priority] = None
    assigned_to_id: Optional[int] = None


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=3000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_id: int
    body: str
    created_at: datetime


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int
    action: str
    created_at: datetime


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject: str
    description: str
    category: Category
    priority: Priority
    status: TicketStatus
    student_id: int
    assigned_to_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    due_at: datetime
    resolved_at: Optional[datetime]


class TicketDetail(TicketOut):
    comments: list[CommentOut] = []
    activity: list[ActivityOut] = []


class Dashboard(BaseModel):
    total: int
    open: int
    in_progress: int
    pending: int
    resolved: int
    breached: int


SLA_HOURS = {Priority.LOW: (24, 72), Priority.MEDIUM: (12, 48), Priority.HIGH: (4, 24), Priority.URGENT: (1, 8)}
TRANSITIONS = {
    TicketStatus.OPEN: {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS},
    TicketStatus.ASSIGNED: {TicketStatus.IN_PROGRESS, TicketStatus.OPEN},
    TicketStatus.IN_PROGRESS: {TicketStatus.PENDING_STUDENT, TicketStatus.RESOLVED},
    TicketStatus.PENDING_STUDENT: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED},
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.REOPENED},
    TicketStatus.REOPENED: {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED},
    TicketStatus.CLOSED: set(),
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(status_code=401, detail="Invalid authentication credentials")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload.get("sub", 0))
    except (JWTError, TypeError, ValueError):
        raise credentials_error
    user = db.get(User, user_id)
    if not user:
        raise credentials_error
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user
    return checker


def log(db: Session, ticket_id: int, actor_id: int, action: str):
    db.add(Activity(ticket_id=ticket_id, actor_id=actor_id, action=action))


def can_view(ticket: Ticket, user: User) -> bool:
    return user.role in {Role.STAFF, Role.MANAGER} or ticket.student_id == user.id


app = FastAPI(title="EduSupport API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email already registered")
    user = User(name=data.name, email=data.email.lower(), password_hash=pwd_context.hash(data.password), role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/auth/login", response_model=LoginResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    token = jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "user": user}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/tickets", response_model=list[TicketOut])
def list_tickets(search: Optional[str] = None, status_filter: Optional[TicketStatus] = Query(None, alias="status"), priority: Optional[Priority] = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = select(Ticket).order_by(Ticket.created_at.desc())
    if user.role == Role.STUDENT:
        query = query.where(Ticket.student_id == user.id)
    if search:
        query = query.where(Ticket.subject.ilike(f"%{search}%"))
    if status_filter:
        query = query.where(Ticket.status == status_filter)
    if priority:
        query = query.where(Ticket.priority == priority)
    return list(db.scalars(query))


@app.post("/api/tickets", response_model=TicketOut, status_code=201)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.STUDENT))):
    _, resolution = SLA_HOURS[data.priority]
    ticket = Ticket(**data.model_dump(), student_id=user.id, due_at=datetime.now(timezone.utc) + timedelta(hours=resolution))
    db.add(ticket)
    db.flush()
    log(db, ticket.id, user.id, "Ticket created")
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/api/tickets/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket or not can_view(ticket, user):
        raise HTTPException(404, "Ticket not found")
    comments = list(db.scalars(select(Comment).where(Comment.ticket_id == ticket_id).order_by(Comment.created_at)))
    activity = list(db.scalars(select(Activity).where(Activity.ticket_id == ticket_id).order_by(Activity.created_at)))
    return TicketDetail.model_validate({**ticket.__dict__, "comments": comments, "activity": activity})


@app.patch("/api/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.STAFF, Role.MANAGER))):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    changes = data.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] != ticket.status:
        new_status = changes["status"]
        if new_status not in TRANSITIONS[ticket.status]:
            raise HTTPException(422, f"Cannot move ticket from {ticket.status} to {new_status}")
        log(db, ticket.id, user.id, f"Status changed: {ticket.status} -> {new_status}")
        if new_status == TicketStatus.RESOLVED:
            ticket.resolved_at = datetime.now(timezone.utc)
        if new_status == TicketStatus.REOPENED:
            ticket.resolved_at = None
    if "assigned_to_id" in changes:
        assignee = db.get(User, changes["assigned_to_id"])
        if not assignee or assignee.role != Role.STAFF:
            raise HTTPException(422, "Tickets can only be assigned to staff")
        log(db, ticket.id, user.id, f"Assigned to {assignee.name}")
    for key, value in changes.items():
        setattr(ticket, key, value)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/api/tickets/{ticket_id}/comments", response_model=CommentOut, status_code=201)
def comment(ticket_id: int, data: CommentCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket or not can_view(ticket, user):
        raise HTTPException(404, "Ticket not found")
    item = Comment(ticket_id=ticket_id, author_id=user.id, body=data.body)
    db.add(item)
    log(db, ticket_id, user.id, "Comment added")
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/dashboard", response_model=Dashboard)
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = select(Ticket)
    if user.role == Role.STUDENT:
        query = query.where(Ticket.student_id == user.id)
    tickets = list(db.scalars(query))
    now = datetime.now(timezone.utc)
    return Dashboard(total=len(tickets), open=sum(t.status in {TicketStatus.OPEN, TicketStatus.ASSIGNED} for t in tickets), in_progress=sum(t.status in {TicketStatus.IN_PROGRESS, TicketStatus.REOPENED} for t in tickets), pending=sum(t.status == TicketStatus.PENDING_STUDENT for t in tickets), resolved=sum(t.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED} for t in tickets), breached=sum(t.status not in {TicketStatus.RESOLVED, TicketStatus.CLOSED} and t.due_at < now for t in tickets))