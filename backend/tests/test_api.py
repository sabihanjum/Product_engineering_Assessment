import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from app.main import Base, SessionLocal, app, engine, pwd_context, User, Role

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()
db.add(User(name="Test Student", email="test@example.com", password_hash=pwd_context.hash("secret123"), role=Role.STUDENT))
db.commit()
db.close()
client = TestClient(app)


def token():
    response = client.post("/api/auth/login", data={"username": "test@example.com", "password": "secret123"})
    return response.json()["access_token"]


def test_student_can_create_and_list_own_ticket():
    headers = {"Authorization": f"Bearer {token()}"}
    created = client.post("/api/tickets", headers=headers, json={"subject": "Need a transcript", "description": "Please help me get my official transcript.", "category": "Documents", "priority": "MEDIUM"})
    assert created.status_code == 201
    assert client.get("/api/tickets", headers=headers).json()[0]["subject"] == "Need a transcript"


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}