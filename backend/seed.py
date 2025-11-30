# create and set up SQLite db file for development use

import sqlite3
from pathlib import Path

# define path to SQLite database file
DB = Path(__file__).parent / "dev.db"

# SQL statements to create tables
create_user_table = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
"""

create_medications_table = """
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    drug_name TEXT NOT NULL,
    dosage TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    message TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

create_schedule_table = """
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    next_reminder TEXT,
    FOREIGN KEY(medication_id) REFERENCES medications(id) ON DELETE CASCADE
);
"""

create_reminders_table = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL,
    reminder_time TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    FOREIGN KEY(schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
);
"""

create_pharmacies_table = """
CREATE TABLE IF NOT EXISTS pharmacies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    phone TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    is_24_hours INTEGER NOT NULL DEFAULT 0
);
"""

# main function to create the database and tables
def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(create_user_table)
    cur.execute(create_medications_table)
    cur.execute(create_schedule_table)
    cur.execute(create_reminders_table)
    cur.execute(create_pharmacies_table)
    conn.commit()
    conn.close()
    print(f"Database created at {DB}")

if __name__ == "__main__":
    main()