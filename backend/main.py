"""
FastAPI backend for RxminderAPP

Endpoints implemented here:
 - POST /users           -> create a user (stores password hash)
 - DELETE /users/{id}    -> delete a user (cascades manually)
 - POST /prescriptions   -> create medication, schedule, and generated reminders

The DB columns that represent
dates/datetimes are stored as ISO-8601 strings (text) in SQLite using
datetime.isoformat() or date.isoformat().

Setup:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

"""

import sqlite3
import os
from dotenv import load_dotenv
from typing import Optional, List
from datetime import datetime, date, time, timedelta
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, EmailStr, validator
from sqlmodel import create_engine, Session, select
from sqlalchemy import event, text
from models import *
from utils import *

# Configuration
DATABASE_URL = "sqlite:///./dev.db"
engine = create_engine(DATABASE_URL, echo=False)

# load environment configuration for runtime validation
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# validation limits (read from env; fallback to sensible defaults)
MAX_TIMES_PER_DAY = int(os.getenv("MAX_TIMES_PER_DAY", "50"))
DOSAGE_MIN = float(os.getenv("DOSAGE_MIN", "0"))
DOSAGE_MAX = float(os.getenv("DOSAGE_MAX", "1000"))

# Ensure SQLite enforces foreign key constraints (needed for ON DELETE CASCADE to work)
@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

app = FastAPI(title="Rxminder Backend")

# Pydantic Validations
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)


class PrescriptionCreate(BaseModel):
    user_id: int
    drug_name: str
    dosage: str
    frequency: int = Field(..., gt=0)
    # dates as YYYY-MM-DD (date-only). end_date can be omitted for open-ended.
    start_date: str
    end_date: Optional[str] = None
    # optional daily offset where reminders begin (HH:MM). default: 08:00
    start_time: Optional[str] = "08:00"
    message: Optional[str] = None

    @validator("start_date", "end_date")
    def check_date_format(cls, v):
        if v is None:
            return v
        try:
            date.fromisoformat(v)
        except Exception:
            raise ValueError("date must be YYYY-MM-DD")
        return v

    @validator("start_time")
    def check_time_format(cls, v):
        try:
            time.fromisoformat(v)
        except Exception:
            raise ValueError("start_time must be HH:MM or HH:MM:SS")
        return v

    @validator("frequency")
    def check_frequency_limit(cls, v):
        if v is None:
            return v
        if v <= 0:
            raise ValueError("frequency must be > 0")
        if v > MAX_TIMES_PER_DAY:
            raise ValueError(f"frequency must be <= {MAX_TIMES_PER_DAY}")
        return v

    @validator("dosage")
    def check_dosage_range(cls, v):
        try:
            import re

            m = re.search(r"[-+]?[0-9]*\.?[0-9]+", v)
            if not m:
                raise ValueError("dosage must contain a numeric value")
            val = float(m.group(0))
        except Exception:
            raise ValueError("dosage must be a numeric value or contain one")
        if val < DOSAGE_MIN or val > DOSAGE_MAX:
            raise ValueError(f"dosage must be between {DOSAGE_MIN} and {DOSAGE_MAX}")
        return v

    @validator("start_date")
    def check_start_not_past(cls, v):
        # ensure start_date not in the past
        try:
            d = date.fromisoformat(v)
        except Exception:
            return v
        today = date.today()
        if d < today:
            raise ValueError("start_date cannot be in the past")
        return v


class PrescriptionUpdate(BaseModel):
    """Partial update model for prescriptions. All fields optional; when a
    field is omitted we fall back to the current DB value (or raise if missing).
    """
    drug_name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[int] = Field(None, gt=0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    start_time: Optional[str] = None
    message: Optional[str] = None

    @validator("start_date", "end_date")
    def check_date_format(cls, v):
        if v is None:
            return v
        try:
            date.fromisoformat(v)
        except Exception:
            raise ValueError("date must be YYYY-MM-DD")
        return v

    @validator("start_time")
    def check_time_format(cls, v):
        if v is None:
            return v
        try:
            time.fromisoformat(v)
        except Exception:
            raise ValueError("start_time must be HH:MM or HH:MM:SS")
        return v

    @validator("frequency")
    def check_frequency_limit(cls, v):
        if v is None:
            return v
        if v <= 0:
            raise ValueError("frequency must be > 0")
        if v > MAX_TIMES_PER_DAY:
            raise ValueError(f"frequency must be <= {MAX_TIMES_PER_DAY}")
        return v

    @validator("dosage")
    def check_dosage_range(cls, v):
        if v is None:
            return v
        try:
            import re

            m = re.search(r"[-+]?[0-9]*\.?[0-9]+", v)
            if not m:
                raise ValueError("dosage must contain a numeric value")
            val = float(m.group(0))
        except Exception:
            raise ValueError("dosage must be a numeric value or contain one")
        if val < DOSAGE_MIN or val > DOSAGE_MAX:
            raise ValueError(f"dosage must be between {DOSAGE_MIN} and {DOSAGE_MAX}")
        return v

    @validator("start_date")
    def check_start_not_past(cls, v):
        if v is None:
            return v
        try:
            d = date.fromisoformat(v)
        except Exception:
            return v
        today = date.today()
        if d < today:
            raise ValueError("start_date cannot be in the past")
        return v




# API endpoints
@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate):
    """Create a user and store hashed password."""
    with Session(engine) as session:
        # check uniqueness
        statement = select(User).where((User.username == payload.username) | (User.email == payload.email))
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(status_code=409, detail="username or email already exists")

        user = User(username=payload.username, email=payload.email, password_hash=hash_password(payload.password))
        session.add(user)
        session.commit()
        session.refresh(user)
        return {"id": user.id, "username": user.username, "email": user.email}


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    """Delete a user. Rely on DB-level ON DELETE CASCADE to remove related rows. """
    
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        session.delete(user)
        session.commit()
        return None


@app.post("/prescriptions", status_code=status.HTTP_201_CREATED)
def create_prescription(payload: PrescriptionCreate):
    """
    Create medication, schedule, and generate reminders based on `frequency`.

    Workflow implemented here:
    1. Insert medication row (linked to user_id).
    2. Insert schedule row with created_at, start_date, end_date (ISO strings).
     3. Expand reminders by generating `frequency` times-per-day equally spaced
         from `start_time` for every day in range [start_date, end_date].
    4. Insert reminders linking schedule_id and user_id with status 'pending'.
    5. Compute schedule.next_reminder as the earliest reminder after now.
    """
    # validate user exists
    with Session(engine) as session:
        user = session.get(User, payload.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        # create medication
        med = Medication(
            user_id=payload.user_id,
            drug_name=payload.drug_name,
            dosage=payload.dosage,
            frequency=payload.frequency,
            message=payload.message,
        )
        session.add(med)
        session.flush()  # populate med.id

        # create schedule
        now = datetime.utcnow()
        start_date_obj = date.fromisoformat(payload.start_date)
        end_date_obj = date.fromisoformat(payload.end_date) if payload.end_date else start_date_obj

        schedule = Schedule(
            medication_id=med.id,
            created_at=now.isoformat(),
            start_date=start_date_obj.isoformat(),
            end_date=end_date_obj.isoformat() if payload.end_date else None,
            next_reminder=None,
        )
        session.add(schedule)
        session.flush()

        # generate daily times (time objects)
        times = generate_daily_times(payload.frequency, payload.start_time)

        # generate reminders for each day in the inclusive range
        reminder_objs: List[Reminder] = []
        for single_date in daterange(start_date_obj, end_date_obj):
            for t in times:
                dt = datetime.combine(single_date, t)
                # store ISO datetime (UTC-naive local time). If you need tz-aware,
                # convert to UTC-aware before storing.
                reminder_iso = dt.isoformat()
                reminder_objs.append(
                    Reminder(
                        schedule_id=schedule.id,
                        user_id=payload.user_id,
                        reminder_time=reminder_iso,
                        status="pending",
                        message=payload.message,
                    )
                )

        # bulk insert reminders
        session.add_all(reminder_objs)
        session.flush()

        # compute next_reminder (earliest reminder_time > now)
        # parse reminder_time strings back into datetimes and compare
        now_dt = datetime.utcnow()
        next_candidates = [datetime.fromisoformat(r.reminder_time) for r in reminder_objs if datetime.fromisoformat(r.reminder_time) > now_dt]
        if next_candidates:
            next_dt = min(next_candidates)
            schedule.next_reminder = next_dt.isoformat()
        else:
            schedule.next_reminder = None

        session.add(schedule)
        session.commit()

        # refresh to get ids and return a helpful payload
        session.refresh(med)
        session.refresh(schedule)

        return {
            "medication": {"id": med.id, "drug_name": med.drug_name, "dosage": med.dosage},
            "schedule": {"id": schedule.id, "start_date": schedule.start_date, "end_date": schedule.end_date, "next_reminder": schedule.next_reminder},
            "created_reminder_count": len(reminder_objs),
        }


@app.put("/prescriptions/{med_id}", status_code=status.HTTP_200_OK)
def update_prescription(med_id: int, payload: PrescriptionUpdate):
    """
    Update medication record, delete any existing schedule(s) and reminders for
    that medication (relying on DB ON DELETE CASCADE), then create a new
    schedule and regenerated reminders based on the provided info.

    Workflow:
      1. Load medication and existing schedule (if any).
      2. Update medication fields with provided values.
      3. Delete existing schedule(s) (this cascades to reminders via FK).
      4. Build a new schedule using provided values or fallbacks.
      5. Generate reminders and insert; set schedule.next_reminder.
    """
    with Session(engine) as session:
        med = session.get(Medication, med_id)
        if not med:
            raise HTTPException(status_code=404, detail="medication not found")

        # read existing schedule values to use as fallbacks
        existing_schedule = session.exec(select(Schedule).where(Schedule.medication_id == med_id)).first()
        old_start = None
        old_end = None
        if existing_schedule:
            old_start = existing_schedule.start_date
            old_end = existing_schedule.end_date

        # update medication fields
        if payload.drug_name is not None:
            med.drug_name = payload.drug_name
        if payload.dosage is not None:
            med.dosage = payload.dosage
        if payload.frequency is not None:
            med.frequency = payload.frequency
        if payload.message is not None:
            med.message = payload.message

        session.add(med)
        session.flush()

        # delete existing schedules (and cascade to reminders) if present
        if existing_schedule:
            # delete all schedules for this medication
            session.query(Schedule).filter(Schedule.medication_id == med_id).delete(synchronize_session=False)
            session.flush()

        # determine start_date / end_date for new schedule
        if payload.start_date:
            start_date_obj = date.fromisoformat(payload.start_date)
        elif old_start:
            start_date_obj = date.fromisoformat(old_start)
        else:
            raise HTTPException(status_code=400, detail="start_date is required when no existing schedule")

        if payload.end_date:
            end_date_obj = date.fromisoformat(payload.end_date)
        elif old_end:
            end_date_obj = date.fromisoformat(old_end)
        else:
            # if no end_date provided, default to start_date
            end_date_obj = start_date_obj

        if end_date_obj < start_date_obj:
            raise HTTPException(status_code=400, detail="end_date must be >= start_date")

        # determine frequency (prefers payload, then med.frequency)
        frequency = payload.frequency if payload.frequency is not None else (med.frequency or 1)
        if frequency <= 0:
            raise HTTPException(status_code=400, detail="frequency must be > 0")

        # determine start_time for daily spacing
        start_time_str = payload.start_time if payload.start_time is not None else str(os.getenv("DEFAULT_START_TIME", "08:00"))

        # create new schedule
        now = datetime.utcnow()
        new_schedule = Schedule(
            medication_id=med.id,
            created_at=now.isoformat(),
            start_date=start_date_obj.isoformat(),
            end_date=end_date_obj.isoformat() if end_date_obj else None,
            next_reminder=None,
        )
        session.add(new_schedule)
        session.flush()

        # generate new reminders
        times = generate_daily_times(frequency, start_time_str)
        reminder_objs: List[Reminder] = []
        for single_date in daterange(start_date_obj, end_date_obj):
            for t in times:
                dt = datetime.combine(single_date, t)
                reminder_iso = dt.isoformat()
                reminder_objs.append(
                    Reminder(
                        schedule_id=new_schedule.id,
                        user_id=med.user_id,
                        reminder_time=reminder_iso,
                        status="pending",
                        message=payload.message,
                    )
                )

        session.add_all(reminder_objs)
        session.flush()

        # compute next_reminder
        now_dt = datetime.utcnow()
        next_candidates = [datetime.fromisoformat(r.reminder_time) for r in reminder_objs if datetime.fromisoformat(r.reminder_time) > now_dt]
        if next_candidates:
            new_schedule.next_reminder = min(next_candidates).isoformat()
        else:
            new_schedule.next_reminder = None

        session.add(new_schedule)
        session.commit()

        session.refresh(med)
        session.refresh(new_schedule)

        return {
            "medication": {"id": med.id, "drug_name": med.drug_name, "dosage": med.dosage, "frequency": med.frequency},
            "schedule": {"id": new_schedule.id, "start_date": new_schedule.start_date, "end_date": new_schedule.end_date, "next_reminder": new_schedule.next_reminder},
            "created_reminder_count": len(reminder_objs),
        }
    
@app.delete("/prescriptions/{med_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(med_id: int):
    # will delete a prescription and cascade-delete its schedules and reminders.
    with Session(engine) as session:
        med = session.get(Medication, med_id)
        if not med:
            raise HTTPException(status_code=404, detail="medication not found")

        session.delete(med)
        session.commit()
        return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
