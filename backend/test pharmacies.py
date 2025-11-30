import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session, select

import main
from models import Pharmacy


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


def test_create_pharmacy(client):
    """Test creating a pharmacy"""
    payload = {
        "name": "CVS Pharmacy",
        "address": "123 Main St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02101",
        "phone": "617-555-0100",
        "latitude": 42.3601,
        "longitude": -71.0589,
        "is_24_hours": True
    }
    
    resp = client.post("/pharmacies", json=payload)
    assert_response_ok(resp, expected_status=201)
    
    data = resp.json()
    assert data["name"] == "CVS Pharmacy"
    assert data["city"] == "Boston"
    assert data["is_24_hours"] is True
    assert "id" in data


def test_get_pharmacy_by_id(client):
    """Test retrieving a specific pharmacy by ID"""
    # Create a pharmacy first
    payload = {
        "name": "Walgreens",
        "address": "456 Oak Ave",
        "city": "Cambridge",
        "state": "MA",
        "zip_code": "02139",
        "latitude": 42.3736,
        "longitude": -71.1097,
        "is_24_hours": False
    }
    
    create_resp = client.post("/pharmacies", json=payload)
    assert_response_ok(create_resp, expected_status=201)
    pharmacy_id = create_resp.json()["id"]
    
    # Get the pharmacy
    get_resp = client.get(f"/pharmacies/{pharmacy_id}")
    assert_response_ok(get_resp, expected_status=200)
    
    data = get_resp.json()
    assert data["name"] == "Walgreens"
    assert data["city"] == "Cambridge"


def test_get_pharmacy_not_found(client):
    """Test retrieving non-existent pharmacy returns 404"""
    resp = client.get("/pharmacies/9999")
    assert resp.status_code == 404


def test_find_pharmacies_nearby(client):
    """Test finding pharmacies within a radius"""
    # Create multiple pharmacies at different locations
    pharmacies = [
        {
            "name": "CVS Downtown",
            "address": "100 State St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02109",
            "latitude": 42.3588,
            "longitude": -71.0578,  # Very close to search point
            "is_24_hours": True
        },
        {
            "name": "Walgreens Back Bay",
            "address": "200 Boylston St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02116",
            "latitude": 42.3505,
            "longitude": -71.0763,  # ~1.2 miles away
            "is_24_hours": False
        },
        {
            "name": "CVS Cambridge",
            "address": "300 Mass Ave",
            "city": "Cambridge",
            "state": "MA",
            "zip_code": "02139",
            "latitude": 42.3736,
            "longitude": -71.1097,  # ~3.5 miles away
            "is_24_hours": True
        },
        {
            "name": "Rite Aid Somerville",
            "address": "400 Broadway",
            "city": "Somerville",
            "state": "MA",
            "zip_code": "02145",
            "latitude": 42.3875,
            "longitude": -71.0995,  # ~4.5 miles away
            "is_24_hours": False
        }
    ]
    
    for pharmacy in pharmacies:
        resp = client.post("/pharmacies", json=pharmacy)
        assert_response_ok(resp, expected_status=201)
    
    # Search for pharmacies within 2 miles of downtown Boston
    search_resp = client.get(
        "/pharmacies/search",
        params={
            "latitude": 42.3601,
            "longitude": -71.0589,
            "radius_miles": 2.0
        }
    )
    assert_response_ok(search_resp, expected_status=200)
    
    data = search_resp.json()
    assert data["count"] == 2  # Should find CVS Downtown and Walgreens Back Bay
    assert len(data["pharmacies"]) == 2
    
    # Results should be sorted by distance
    assert data["pharmacies"][0]["distance_miles"] < data["pharmacies"][1]["distance_miles"]
    
    # Verify the closest one is CVS Downtown
    assert data["pharmacies"][0]["name"] == "CVS Downtown"


def test_find_pharmacies_24_hours_filter(client):
    """Test filtering for 24-hour pharmacies"""
    # Create pharmacies with different 24-hour status
    pharmacies = [
        {
            "name": "CVS 24hr",
            "address": "100 State St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02109",
            "latitude": 42.3588,
            "longitude": -71.0578,
            "is_24_hours": True
        },
        {
            "name": "Walgreens Regular",
            "address": "200 Boylston St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02116",
            "latitude": 42.3505,
            "longitude": -71.0763,
            "is_24_hours": False
        }
    ]
    
    for pharmacy in pharmacies:
        resp = client.post("/pharmacies", json=pharmacy)
        assert_response_ok(resp, expected_status=201)
    
    # Search for only 24-hour pharmacies
    search_resp = client.get(
        "/pharmacies/search",
        params={
            "latitude": 42.3601,
            "longitude": -71.0589,
            "radius_miles": 5.0,
            "is_24_hours": True
        }
    )
    assert_response_ok(search_resp, expected_status=200)
    
    data = search_resp.json()
    assert data["count"] == 1
    assert data["pharmacies"][0]["name"] == "CVS 24hr"
    assert data["pharmacies"][0]["is_24_hours"] is True


def test_find_pharmacies_no_results(client):
    """Test search with no pharmacies in range"""
    # Create a pharmacy far away
    payload = {
        "name": "Distant Pharmacy",
        "address": "999 Far Away St",
        "city": "Springfield",
        "state": "MA",
        "zip_code": "01101",
        "latitude": 42.1015,
        "longitude": -72.5898,  # Springfield, MA - about 90 miles away
        "is_24_hours": False
    }
    
    resp = client.post("/pharmacies", json=payload)
    assert_response_ok(resp, expected_status=201)
    
    # Search in Boston with small radius
    search_resp = client.get(
        "/pharmacies/search",
        params={
            "latitude": 42.3601,
            "longitude": -71.0589,
            "radius_miles": 5.0
        }
    )
    assert_response_ok(search_resp, expected_status=200)
    
    data = search_resp.json()
    assert data["count"] == 0
    assert data["pharmacies"] == []


def test_pharmacy_validation_invalid_coordinates(client):
    """Test that invalid coordinates are rejected"""
    # Invalid latitude (> 90)
    payload = {
        "name": "Bad Pharmacy",
        "address": "123 Invalid St",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02101",
        "latitude": 95.0,  # Invalid
        "longitude": -71.0589,
        "is_24_hours": False
    }
    
    resp = client.post("/pharmacies", json=payload)
    assert resp.status_code == 422  # Validation error
    
    # Invalid longitude (< -180)
    payload["latitude"] = 42.3601
    payload["longitude"] = -190.0  # Invalid
    
    resp = client.post("/pharmacies", json=payload)
    assert resp.status_code == 422


def test_search_radius_validation(client):
    """Test that search radius is validated"""
    # Radius too large (> 50)
    resp = client.get(
        "/pharmacies/search",
        params={
            "latitude": 42.3601,
            "longitude": -71.0589,
            "radius_miles": 100.0  # Too large
        }
    )
    assert resp.status_code == 422
    
    # Radius zero or negative
    resp = client.get(
        "/pharmacies/search",
        params={
            "latitude": 42.3601,
            "longitude": -71.0589,
            "radius_miles": 0
        }
    )
    assert resp.status_code == 422


def test_distance_calculation_accuracy(client):
    """Test that distance calculation is reasonably accurate"""
    # Create a pharmacy at a known distance
    # MIT is approximately 1.8 miles from Boston Common
    payload = {
        "name": "MIT Pharmacy",
        "address": "77 Massachusetts Ave",
        "city": "Cambridge",
        "state": "MA",
        "zip_code": "02139",
        "latitude": 42.3601,
        "longitude": -71.0942,  # MIT
        "is_24_hours": False
    }
    
    resp = client.post("/pharmacies", json=payload)
    assert_response_ok(resp, expected_status=201)
    
    # Search from Boston Common
    search_resp = client.get(
        "/pharmacies/search",
        params={
            "latitude": 42.3551,  # Boston Common
            "longitude": -71.0656,
            "radius_miles": 5.0
        }
    )
    assert_response_ok(search_resp, expected_status=200)
    
    data = search_resp.json()
    assert data["count"] == 1
    
    # Distance should be approximately 1.8 miles (allow some margin)
    distance = data["pharmacies"][0]["distance_miles"]
    assert 1.4 < distance < 2.2  # Reasonable range for the actual distance