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

# tests POST /users and duplicate user handling
def test_create_user_and_duplicate(client):
    payload = {"username": "alice", "email": "alice@example.com", "password": "sadddd"}
    resp = client.post("/users", json=payload)
    assert_response_ok(resp, expected_status=201)
    data = resp.json()
    assert data["username"] == "alice"

    # duplicate should fail
    resp2 = client.post("/users", json=payload)
    assert resp2.status_code == 409

# tests POST, PUT, DELETE /prescriptions and DELETE /users (with cascade)
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

# tests POST /prescriptions with bad date format
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

# tests POST /prescriptions with invalid start_date (in the past)
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

# tests POST /prescriptions with frequency exceeding MAX_TIMES_PER_DAY
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

# tests POST /prescriptions with dosage outside allowed bounds
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

# tests DELETE /users with cascade deletion of related prescriptions
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

# tests DELETE /prescriptions with cascade deletion of schedule and reminders
def test_prescription_delete_cascade(client):
    # Create user
    payload = {"username": "d1333", "email": "d1@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    # Create a prescription (single day, freq 2)
    pres_payload = {
        "user_id": user_id,
        "drug_name": "ToDelete",
        "dosage": "5 mg",
        "frequency": 2,
        "start_date": date.today().isoformat(),
        "end_date": date.today().isoformat(),
        "start_time": "08:00",
    }
    r2 = client.post("/prescriptions", json=pres_payload)
    assert_response_ok(r2, expected_status=201)
    data = r2.json()
    med_id = data["medication"]["id"]
    schedule_id = data["schedule"]["id"]

    # Verify DB rows exist
    with Session(main.engine) as sess:
        assert sess.get(Medication, med_id) is not None
        assert sess.get(Schedule, schedule_id) is not None
        reminders = sess.exec(select(Reminder).where(Reminder.schedule_id == schedule_id)).all()
        assert len(reminders) > 0

    # Delete the prescription
    dr = client.delete(f"/prescriptions/{med_id}")
    assert_response_ok(dr, expected_status=204)

    # Verify medication, schedule, reminders are all gone
    with Session(main.engine) as sess:
        assert sess.get(Medication, med_id) is None
        schedules = sess.exec(select(Schedule).where(Schedule.medication_id == med_id)).all()
        assert schedules == []
        reminders = sess.exec(select(Reminder).where(Reminder.schedule_id == schedule_id)).all()
        assert reminders == []

    # User should still exist
    with Session(main.engine) as sess:
        assert sess.get(User, user_id) is not None

# tests DELETE /prescriptions for non-existent prescription
def test_prescription_delete_not_found(client):
    r = client.delete("/prescriptions/9999")
    assert r.status_code == 404

# tests GET /prescriptions listing for a user
def test_list_prescriptions(client):
    # create user
    payload = {"username": "listuser", "email": "list@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    # prescription 1: single day, frequency 2
    start = date.today()
    pres1 = {
        "user_id": user_id,
        "drug_name": "ListDrugOne",
        "dosage": "5 mg",
        "frequency": 2,
        "start_date": start.isoformat(),
        "end_date": start.isoformat(),
        "start_time": "08:00",
    }
    r1 = client.post("/prescriptions", json=pres1)
    assert_response_ok(r1, expected_status=201)
    created1 = r1.json()
    med1_id = created1["medication"]["id"]
    count1 = created1["created_reminder_count"]

    # prescription 2: two days, frequency 3
    end = start + timedelta(days=1)
    pres2 = {
        "user_id": user_id,
        "drug_name": "ListDrugTwo",
        "dosage": "10 mg",
        "frequency": 3,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "start_time": "09:00",
    }
    r2 = client.post("/prescriptions", json=pres2)
    assert_response_ok(r2, expected_status=201)
    created2 = r2.json()
    med2_id = created2["medication"]["id"]
    count2 = created2["created_reminder_count"]

    # call list endpoint
    rl = client.get(f"/prescriptions/{user_id}")
    assert_response_ok(rl, expected_status=200)
    data = rl.json()
    assert isinstance(data, list)

    # find entries for the two medications
    entry1 = next((e for e in data if e["medication"]["id"] == med1_id), None)
    entry2 = next((e for e in data if e["medication"]["id"] == med2_id), None)
    assert entry1 is not None, "Missing first medication in list response"
    assert entry2 is not None, "Missing second medication in list response"

    # verify fields and reminder counts
    for entry, expected_count in ((entry1, count1), (entry2, count2)):
        med = entry["medication"]
        assert med["user_id"] == user_id
        assert "drug_name" in med and "dosage" in med and "frequency" in med
        # schedule may be present; when present check keys
        if entry["schedule"] is not None:
            sched = entry["schedule"]
            assert "start_date" in sched and "next_reminder" in sched
        assert isinstance(entry["reminder_count"], int)
        assert entry["reminder_count"] == expected_count


# Verify that PUT /prescriptions/{med_id} updates medication fields,
# regenerates reminders according to new frequency/start_time, and
# returns the updated medication + schedule + created_reminder_count.
def test_update_prescription_basic(client):
    # create user
    payload = {"username": "upduser", "email": "upd@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    # create initial prescription: 2 days, freq 3
    start = date.today()
    end = start + timedelta(days=1)
    pres = {
        "user_id": user_id,
        "drug_name": "UpdateDrug",
        "dosage": "10 mg",
        "frequency": 3,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "start_time": "08:00",
    }
    r1 = client.post("/prescriptions", json=pres)
    assert_response_ok(r1, expected_status=201)
    created = r1.json()
    med_id = created["medication"]["id"]

    # perform update: change frequency to 2 and start_time
    upd = {"frequency": 2, "start_time": "09:00", "drug_name": "UpdatedName", "message": "New note"}
    r2 = client.put(f"/prescriptions/{med_id}", json=upd)
    assert_response_ok(r2, expected_status=200)
    updated = r2.json()
    # frequency updated and reminder count recalculated (2 days * 2 times/day)
    assert updated["medication"]["frequency"] == 2
    assert updated["created_reminder_count"] == 2 * 2
    assert updated["medication"]["drug_name"] == "UpdatedName"



# Test PUT /prescriptionss returns 422 for bad formats and 400 for business logic errors
def test_update_prescription_validation_errors(client):
    # create user and prescription
    payload = {"username": "valuser", "email": "val@example.com", "password": "pw12345"}
    r = client.post("/users", json=payload)
    assert_response_ok(r, expected_status=201)
    user_id = r.json()["id"]

    pres = {
        "user_id": user_id,
        "drug_name": "ValDrug",
        "dosage": "5 mg",
        "frequency": 2,
        "start_date": date.today().isoformat(),
        "end_date": date.today().isoformat(),
        "start_time": "08:00",
    }
    r1 = client.post("/prescriptions", json=pres)
    assert_response_ok(r1, expected_status=201)
    med_id = r1.json()["medication"]["id"]

    # invalid date format -> 422
    r_bad_date = client.put(f"/prescriptions/{med_id}", json={"start_date": "not-a-date"})
    assert r_bad_date.status_code == 422

    # end_date before start_date -> 400
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()
    r_end_before = client.put(f"/prescriptions/{med_id}", json={"start_date": today, "end_date": yesterday})
    assert r_end_before.status_code == 400

    # frequency too large -> 422
    too_many = main.MAX_TIMES_PER_DAY + 1
    r_freq = client.put(f"/prescriptions/{med_id}", json={"frequency": too_many})
    assert r_freq.status_code == 422

    # dosage out of bounds -> 422
    too_big = main.DOSAGE_MAX + 1000
    r_dose = client.put(f"/prescriptions/{med_id}", json={"dosage": f"{too_big} mg"})
    assert r_dose.status_code == 422


# Test PUT /prescriptions updating non-existent prescription returns 404
def test_update_prescription_not_found(client):
    r = client.put("/prescriptions/9999", json={"frequency": 2})
    assert r.status_code == 404

# subuser logic tests
def test_create_subuser(client):
    # Create parent user
    parent = {
        "username": "parentA",
        "email": "parentA@example.com",
        "password": "pw12345"
    }
    r = client.post("/users", json=parent)
    assert_response_ok(r, expected_status=201)
    parent_id = r.json()["id"]

    # Create subuser
    sub = {
        "username": "childA",
        "email": "childA@example.com",
        "password": "pwchild"
    }
    r2 = client.post(f"/users/{parent_id}/subusers", json=sub)
    assert_response_ok(r2, expected_status=201)

    data = r2.json()
    assert data["parent_user_id"] == parent_id
    assert data["email"] == "childA@example.com"
