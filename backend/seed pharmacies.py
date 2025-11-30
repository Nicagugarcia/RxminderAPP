"""
Seed script to populate the database with sample pharmacy data.
Run this after setting up the database with seed.py
"""

import sqlite3
from pathlib import Path

# define path to SQLite database file
DB = Path(__file__).parent / "dev.db"

# Sample pharmacy data for Boston area
sample_pharmacies = [
    {
        "name": "CVS Pharmacy - Downtown Crossing",
        "address": "587 Washington St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02111",
        "phone": "617-542-2369",
        "latitude": 42.3552,
        "longitude": -71.0606,
        "is_24_hours": 0
    },
    {
        "name": "Walgreens - Beacon Hill",
        "address": "24 School St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02108",
        "phone": "617-227-0924",
        "latitude": 42.3587,
        "longitude": -71.0603,
        "is_24_hours": 1
    },
    {
        "name": "CVS Pharmacy - Back Bay",
        "address": "230 Newbury St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02116",
        "phone": "617-236-1692",
        "latitude": 42.3505,
        "longitude": -71.0832,
        "is_24_hours": 0
    },
    {
        "name": "Rite Aid - Cambridge",
        "address": "625 Massachusetts Ave",
        "city": "Cambridge",
        "state": "MA",
        "zip_code": "02139",
        "phone": "617-876-4405",
        "latitude": 42.3677,
        "longitude": -71.1040,
        "is_24_hours": 0
    },
    {
        "name": "CVS Pharmacy - Harvard Square",
        "address": "1426 Massachusetts Ave",
        "city": "Cambridge",
        "state": "MA",
        "zip_code": "02138",
        "phone": "617-876-5219",
        "latitude": 42.3770,
        "longitude": -71.1167,
        "is_24_hours": 1
    },
    {
        "name": "Walgreens - Somerville",
        "address": "343 Broadway",
        "city": "Somerville",
        "state": "MA",
        "zip_code": "02145",
        "phone": "617-666-1230",
        "latitude": 42.3892,
        "longitude": -71.0990,
        "is_24_hours": 0
    },
    {
        "name": "CVS Pharmacy - Brookline",
        "address": "1330 Beacon St",
        "city": "Brookline",
        "state": "MA",
        "zip_code": "02446",
        "phone": "617-232-2221",
        "latitude": 42.3398,
        "longitude": -71.1214,
        "is_24_hours": 0
    },
    {
        "name": "Walgreens - South End",
        "address": "606 Tremont St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02118",
        "phone": "617-236-1382",
        "latitude": 42.3451,
        "longitude": -71.0708,
        "is_24_hours": 1
    },
    {
        "name": "CVS Pharmacy - Fenway",
        "address": "1266 Boylston St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02215",
        "phone": "617-267-8651",
        "latitude": 42.3472,
        "longitude": -71.0995,
        "is_24_hours": 0
    },
    {
        "name": "Rite Aid - Allston",
        "address": "434 Cambridge St",
        "city": "Allston",
        "state": "MA",
        "zip_code": "02134",
        "phone": "617-254-5505",
        "latitude": 42.3634,
        "longitude": -71.1312,
        "is_24_hours": 0
    }
]


def seed_pharmacies():
    """Insert sample pharmacy data into the database"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Check if pharmacies table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pharmacies'")
    if not cur.fetchone():
        print("Error: pharmacies table does not exist. Please run seed.py first.")
        conn.close()
        return
    
    # Insert sample data
    for pharmacy in sample_pharmacies:
        cur.execute("""
            INSERT INTO pharmacies (name, address, city, state, zip_code, phone, latitude, longitude, is_24_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pharmacy["name"],
            pharmacy["address"],
            pharmacy["city"],
            pharmacy["state"],
            pharmacy["zip_code"],
            pharmacy["phone"],
            pharmacy["latitude"],
            pharmacy["longitude"],
            pharmacy["is_24_hours"]
        ))
    
    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(sample_pharmacies)} pharmacies into the database")


if __name__ == "__main__":
    seed_pharmacies()