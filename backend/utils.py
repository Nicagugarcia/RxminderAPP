from typing import List
from datetime import date, time, timedelta
from passlib.context import CryptContext
from models import *

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Utility helpers
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def daterange(start: date, end: date):
    """Yield dates from start to end inclusive."""
    for n in range((end - start).days + 1):
        yield start + timedelta(days=n)


def generate_daily_times(frequency: int, start_time_str: str) -> List[time]:
    """Return a list of `frequency` time objects equally spaced across 24h

    We use the provided `start_time_str` as the offset. Spacing is computed as
    interval = 24h / frequency and times are (start + k*interval) % 24h.
    """
    if frequency <= 0:
        return []

    # parse start_time (HH:MM or HH:MM:SS)
    st = time.fromisoformat(start_time_str)
    start_seconds = st.hour * 3600 + st.minute * 60 + st.second
    interval = 86400 / frequency
    times: List[time] = []
    for k in range(frequency):
        sec = int((start_seconds + k * interval) % 86400)
        hh = sec // 3600
        mm = (sec % 3600) // 60
        ss = sec % 60
        times.append(time(hour=hh, minute=mm, second=ss))
    return times