import json
from pathlib import Path
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy import text

import main
from models import User, Medication, Schedule, Reminder


def assert_response_ok(resp, expected_status=200):
    if resp.status_code != expected_status:
        raise AssertionError(f"Expected status {expected_status}, got {resp.status_code}: {resp.text}")


@pytest.fixture
def client(tmp_path):
    # create a temp sqlite file per test
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"

    # create engine for this test
    engine = create_engine(db_url, connect_args={"check_same_thread": False}, echo=True)

    # ensure SQLite enforces foreign keys on this engine
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    # create tables from your SQLModel metadata
    SQLModel.metadata.create_all(engine)

    # rebind the app's engine so endpoints use this test DB
    main.engine = engine

    # create client and yield to test
    client = TestClient(main.app)
    try:
        yield client
    finally:
        # teardown: drop all tables and dispose engine to fully clear DB
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def test_create_user_and_duplicate(client):
    payload = {"username": "alice", "email": "alice@example.com", "password": "sadddd"}
    resp = client.post("/users", json=payload)
    assert_response_ok(resp, expected_status=201)
    data = resp.json()
    assert data["username"] == "alice"

    # duplicate should fail
    resp2 = client.post("/users", json=payload)
    assert resp2.status_code == 409


def test_prescription_create_and_update_and_delete_cascade(client):
    # create user
    payload = {"username": "bob", "email": "bob@example.com", "password": "hunter2"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user = r.json()
    user_id = user["id"]

    # create a prescription for 2 days, 3 times per day
    start = date.today()
    end = start + timedelta(days=1)
    pres_payload = {
        "user_id": user_id,
        "drug_name": "TestDrug",
        "dosage": "10 mg",
        "frequency": 3,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "start_time": "08:00",
        "message": "Take with food",
    }

    r2 = client.post("/prescriptions", json=pres_payload)
    assert_response_ok(r2, expected_status=201)
    created = r2.json()
    assert created["created_reminder_count"] == 3 * 2
    med_id = created["medication"]["id"]
    schedule_id = created["schedule"]["id"]

    # update prescription: change frequency to 2
    upd = {"frequency": 2, "start_time": "09:00"}
    r3 = client.put(f"/prescriptions/{med_id}", json=upd)
    assert_response_ok(r3, expected_status=200)
    updated = r3.json()
    assert updated["medication"]["frequency"] == 2
    assert updated["created_reminder_count"] == 2 * 2

    # delete user and verify cascade: medication, schedule, reminders removed
    delr = client.delete(f"/users/{user_id}")
    assert_response_ok(delr, expected_status=204)

    # direct DB checks: open a session on main.engine
    with Session(main.engine) as sess:
        meds = sess.exec(select(Medication).where(Medication.user_id == user_id)).all()
        assert meds == []
        schedules = sess.exec(select(Schedule).where(Schedule.medication_id == med_id)).all()
        assert schedules == []
        reminders = sess.exec(select(Reminder).where(Reminder.schedule_id == schedule_id)).all()
        assert reminders == []


def test_prescription_bad_date_validation(client):
    # create user
    payload = {"username": "cathy", "email": "cathy@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    bad = {
        "user_id": user_id,
        "drug_name": "X",
        "dosage": "1",
        "frequency": 1,
        "start_date": "not-a-date",
    }
    r2 = client.post("/prescriptions", json=bad)
    # FastAPI/Pydantic will return 422 for validation error
    assert r2.status_code == 422


def test_start_date_not_in_past(client):
    # create user
    payload = {"username": "pastuser", "email": "past@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    # start_date in the past should be rejected
    past_date = date.today() - timedelta(days=1)
    pres = {
        "user_id": user_id,
        "drug_name": "PastDrug",
        "dosage": "10 mg",
        "frequency": 1,
        "start_date": past_date.isoformat(),
    }
    r2 = client.post("/prescriptions", json=pres)
    assert r2.status_code == 422


def test_times_per_day_limits(client):
    # create user
    payload = {"username": "frequser", "email": "freq@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    # too large frequency should be rejected
    too_many = main.MAX_TIMES_PER_DAY + 1
    pres_bad = {
        "user_id": user_id,
        "drug_name": "FreqDrug",
        "dosage": "10 mg",
        "frequency": too_many,
        "start_date": date.today().isoformat(),
    }
    r_bad = client.post("/prescriptions", json=pres_bad)
    assert r_bad.status_code == 422

    # boundary value (equal to MAX_TIMES_PER_DAY) should be accepted
    pres_ok = {**pres_bad, "frequency": main.MAX_TIMES_PER_DAY}
    r_ok = client.post("/prescriptions", json=pres_ok)
    assert_response_ok(r_ok, expected_status=201)


def test_dosage_bounds(client):
    # create user
    payload = {"username": "doseuser", "email": "dose@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    # below minimum
    below = main.DOSAGE_MIN - 1 if main.DOSAGE_MIN >= 1 else main.DOSAGE_MIN - 0.1
    pres_low = {
        "user_id": user_id,
        "drug_name": "LowDrug",
        "dosage": f"{below} mg",
        "frequency": 1,
        "start_date": date.today().isoformat(),
    }
    r_low = client.post("/prescriptions", json=pres_low)
    assert r_low.status_code == 422

    # above maximum
    above = main.DOSAGE_MAX + 1
    pres_high = {**pres_low, "dosage": f"{above} mg"}
    r_high = client.post("/prescriptions", json=pres_high)
    assert r_high.status_code == 422

    # edge values (exact min and max) should be accepted
    pres_min = {**pres_low, "dosage": f"{main.DOSAGE_MIN} mg"}
    r_min = client.post("/prescriptions", json=pres_min)
    assert_response_ok(r_min, expected_status=201)

    pres_max = {**pres_low, "dosage": f"{main.DOSAGE_MAX} mg"}
    r_max = client.post("/prescriptions", json=pres_max)
    assert_response_ok(r_max, expected_status=201)


def test_delete_user_cascade_only(client):
    # create user
    payload = {"username": "deluser", "email": "del@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]
    print(f"Created user with ID {user_id}")

    # create a single-day prescription so we can check entries
    pres_payload = {
        "user_id": user_id,
        "drug_name": "CascadeDrug",
        "dosage": "5 mg",
        "frequency": 2,
        "start_date": date.today().isoformat(),
        "end_date": date.today().isoformat(),
        "start_time": "08:00",
    }
    r2 = client.post("/prescriptions", json=pres_payload)
    assert_response_ok(r2, expected_status=201)
    created = r2.json()
    med_id = created["medication"]["id"]
    schedule_id = created["schedule"]["id"]

    # confirm entries exist in DB
    with Session(main.engine) as sess:
        meds = sess.exec(select(Medication).where(Medication.user_id == user_id)).all()
        assert len(meds) == 1
        schedules = sess.exec(select(Schedule).where(Schedule.medication_id == med_id)).all()
        assert len(schedules) >= 1
        reminders = sess.exec(select(Reminder).where(Reminder.schedule_id == schedule_id)).all()
        assert len(reminders) > 0

    # delete user and verify cascade removed related rows
    dr = client.delete(f"/users/{user_id}")
    assert_response_ok(dr, expected_status=204)

    with Session(main.engine) as sess:
        assert sess.exec(select(User).where(User.id == user_id)).first() is None
        meds = sess.exec(select(Medication).where(Medication.user_id == user_id)).all()
        assert meds == []
        schedules = sess.exec(select(Schedule).where(Schedule.medication_id == med_id)).all()
        assert schedules == []
        reminders = sess.exec(select(Reminder).where(Reminder.schedule_id == schedule_id)).all()
        assert reminders == []
