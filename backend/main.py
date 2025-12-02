"""
FastAPI backend for RxminderAPP

Endpoints implemented here:
 - POST /users           -> create a user (stores password hash)
 - DELETE /users/{id}    -> delete a user (cascades manually)
 - POST /prescriptions   -> create medication, schedule, and generated reminders
 - GET /pharmacies       -> search for nearby pharmacies using Google Places API

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
import requests
from models import *
from utils import *
from fastapi.middleware.cors import CORSMiddleware


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

# CORS middleware, intentionally loose for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Google Places API configuration
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

# Pydantic Validations
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=6)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

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

        user = User(username=payload.username, email=payload.email, password_hash=hash_password(payload.password), parent_user_id=None,)
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
    

@app.post("/login", status_code=status.HTTP_200_OK)
def login(payload:LoginRequest):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == payload.email)).first()
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="invalid credentials")
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "parent_user_id": user.parent_user_id,
        }

@app.post("/users/{parent_id}/subusers", status_code=status.HTTP_201_CREATED)
def create_subuser(parent_id: int, payload: UserCreate):
    with Session(engine) as session:
        parent = session.get(User, parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="parent user not found")

        existing = session.exec(
            select(User).where(
                (User.username == payload.username) |
                (User.email == payload.email)
            )
        ).first()

        if existing:
            raise HTTPException(status_code=409, detail="username or email already exists")

        sub = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            parent_user_id=parent_id
        )

        session.add(sub)
        session.commit()
        session.refresh(sub)

        return {
            "id": sub.id,
            "username": sub.username,
            "email": sub.email,
            "parent_user_id": sub.parent_user_id
        }




@app.get("/prescriptions/{user_id}", status_code=status.HTTP_200_OK)
def list_prescriptions(user_id: int):
    """
    List prescriptions for a user.
    - Query param: user_id
    - Response: list of objects:
      {
        "medication": { id, drug_name, dosage, frequency, message, user_id },
        "schedule": { id, start_date, end_date, next_reminder } | null,
        "reminder_count": int
      }
    """

    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        owner_id = user.parent_user_id or user.id
        meds = session.exec(select(Medication).where(Medication.user_id == owner_id)).all()
        
        out = []
        for med in meds:
            # get latest schedule for this medication (by created_at desc)
            sched_stmt = select(Schedule).where(Schedule.medication_id == med.id).order_by(text("created_at DESC"))
            schedule = session.exec(sched_stmt).first()

            reminder_count = 0
            if schedule:
                reminders = session.exec(select(Reminder).where(Reminder.schedule_id == schedule.id)).all()
                reminder_count = len(reminders)

            out.append({
                "medication": {
                    "id": med.id,
                    "user_id": med.user_id,
                    "drug_name": med.drug_name,
                    "dosage": med.dosage,
                    "frequency": med.frequency,
                    "message": med.message,
                },
                "schedule": {
                    "id": schedule.id,
                    "start_date": schedule.start_date,
                    "end_date": schedule.end_date,
                    "next_reminder": schedule.next_reminder,
                } if schedule else None,
                "reminder_count": reminder_count,
            })

        return out
    
def create_subuser(parent_id: int, payload: UserCreate):
    """
    Create a subuser linked to a parent user.
    - parent_id: ID of the main/primary user.
    """
    with Session(engine) as session:
        parent = session.get(User, parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="parent user not found")

        # enforce unique username/email across all users
        existing = session.exec(
            select(User).where(
                (User.username == payload.username) | (User.email == payload.email)
            )
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="username or email already exists")

        sub = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            parent_user_id=parent_id,
        )
        session.add(sub)
        session.commit()
        session.refresh(sub)

        return {
            "id": sub.id,
            "username": sub.username,
            "email": sub.email,
            "parent_user_id": sub.parent_user_id,
        }

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


@app.get("/reminders/{user_id}", status_code=status.HTTP_200_OK)
def get_user_reminders(user_id: int):
    """
    For each medication owned by `user_id`, return one reminder entry constructed
    from the schedule.next_reminder. After constructing the response for a
    schedule, mark the corresponding reminder record with that reminder_time
    as status='scheduled', then advance the schedule.next_reminder to the
    earliest reminder for that schedule that remains with status='pending'.

    Response: a JSON list of objects:
    {
      "trigger_time": <ISO string>,
      "med_name": <string>,
      "dosage": <string>,
      "message": <string>
    }
    """

    out = []
    with Session(engine) as session:
        # fetch all medications for this user
        meds = session.exec(select(Medication).where(Medication.user_id == user_id)).all()

        for med in meds:
            # get the most-recent schedule for this medication (by created_at desc)
            sched_stmt = select(Schedule).where(Schedule.medication_id == med.id).order_by(text("created_at DESC"))
            schedule = session.exec(sched_stmt).first()
            if not schedule:
                # no schedule for this medication -> skip
                continue

            next_rem = schedule.next_reminder
            if not next_rem:
                # nothing scheduled currently -> skip
                continue

            # construct response entry using schedule.next_reminder and medication fields
            entry = {
                "trigger_time": next_rem,
                "med_name": med.drug_name,
                "dosage": med.dosage,
                "message": med.message or "",
            }
            out.append(entry)

            # find the reminder record that corresponds to this next_reminder and mark it 'scheduled'
            rem_stmt = select(Reminder).where(
                Reminder.schedule_id == schedule.id,
                Reminder.reminder_time == next_rem
            )
            rem = session.exec(rem_stmt).first()
            if rem:
                rem.status = "scheduled"
                session.add(rem)

            # find the earliest pending reminder for this schedule and set schedule.next_reminder to it
            pending_stmt = select(Reminder).where(
                Reminder.schedule_id == schedule.id,
                Reminder.status == "pending"
            ).order_by(text("reminder_time ASC"))
            next_pending = session.exec(pending_stmt).first()
            if next_pending:
                schedule.next_reminder = next_pending.reminder_time
            else:
                schedule.next_reminder = None

            session.add(schedule)

        # persist all changes
        session.commit()

    return out


@app.get("/pharmacies")
async def search_pharmacies(
    latitude: float,
    longitude: float,
    radius: int = 5000,  # meters, default 5km
):
    """
    Search for nearby pharmacies using Google Places API.
    
    Args:
        latitude: User's latitude (-90 to 90)
        longitude: User's longitude (-180 to 180)
        radius: Search radius in meters (500 to 50000)
    
    Returns:
        List of pharmacies with name, address, location, rating, etc.
    """
    # Validate inputs
    if not (-90 <= latitude <= 90):
        raise HTTPException(status_code=400, detail="Invalid latitude")
    if not (-180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Invalid longitude")
    if not (500 <= radius <= 50000):
        raise HTTPException(status_code=400, detail="Radius must be between 500m and 50km")
    
    if not GOOGLE_PLACES_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Google Places API key not configured"
        )
    
    # Build request to Google Places API
    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius,
        "type": "pharmacy",
        "key": GOOGLE_PLACES_API_KEY,
    }
    
    try:
        response = requests.get(PLACES_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "OK":
            return {"pharmacies": [], "status": data.get("status"), "count": 0}
        
        # Transform results to our format
        pharmacies = []
        for place in data.get("results", []):
            pharmacy = {
                "place_id": place.get("place_id"),
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "latitude": place.get("geometry", {}).get("location", {}).get("lat"),
                "longitude": place.get("geometry", {}).get("location", {}).get("lng"),
                "rating": place.get("rating"),
                "open_now": place.get("opening_hours", {}).get("open_now"),
                "icon": place.get("icon"),
            }
            pharmacies.append(pharmacy)
        
        return {
            "pharmacies": pharmacies,
            "count": len(pharmacies),
            "status": "OK"
        }
        
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch pharmacies: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)