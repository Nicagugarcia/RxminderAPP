from typing import Optional, List
from sqlmodel import SQLModel, Field as ORMField, create_engine, Session, select
from sqlalchemy import Column, ForeignKey

# DB models
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = ORMField(default=None, primary_key=True)
    username: str = ORMField(index=True)
    email: str = ORMField(index=True)
    password_hash: str


class Medication(SQLModel, table=True):
    __tablename__ = "medications"
    id: Optional[int] = ORMField(default=None, primary_key=True)
    user_id: int = ORMField(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE")))
    drug_name: str
    dosage: str
    frequency: int  # times per day
    message: Optional[str] = None


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"
    id: Optional[int] = ORMField(default=None, primary_key=True)
    medication_id: int = ORMField(sa_column=Column(ForeignKey("medications.id", ondelete="CASCADE")))
    created_at: str  # ISO datetime string
    start_date: str  # ISO date string (YYYY-MM-DD)
    end_date: Optional[str] = None  # ISO date string (YYYY-MM-DD)
    next_reminder: Optional[str] = None  # ISO datetime string


class Reminder(SQLModel, table=True):
    __tablename__ = "reminders"
    id: Optional[int] = ORMField(default=None, primary_key=True)
    schedule_id: int = ORMField(sa_column=Column(ForeignKey("schedules.id", ondelete="CASCADE")))
    reminder_time: str  # ISO datetime string
    status: str = "pending"  # default status
    message: Optional[str] = None

class Pharmacy(SQLModel, table=True):
    __tablename__ = "pharmacies"
    id: Optional[int] = ORMField(default=None, primary_key=True)
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str] = None
    latitude: float
    longitude: float
    is_24_hours: bool = False