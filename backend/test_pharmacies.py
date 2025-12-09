"""
Tests for the pharmacy search endpoint (/pharmacies)

Run with: pytest test_pharmacies.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

import requests
from main import app

client = TestClient(app)


# Mock response data
MOCK_GOOGLE_RESPONSE_SUCCESS = {
    "results": [
        {
            "place_id": "ChIJ123",
            "name": "CVS Pharmacy",
            "vicinity": "123 Main St, Brookline",
            "geometry": {
                "location": {
                    "lat": 42.3318,
                    "lng": -71.1211
                }
            },
            "rating": 4.2,
            "opening_hours": {
                "open_now": True
            },
            "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/pharmacy-71.png"
        },
        {
            "place_id": "ChIJ456",
            "name": "Walgreens",
            "vicinity": "456 Beacon St, Brookline",
            "geometry": {
                "location": {
                    "lat": 42.3456,
                    "lng": -71.1234
                }
            },
            "rating": 3.8,
            "opening_hours": {
                "open_now": False
            },
            "icon": "https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/pharmacy-71.png"
        }
    ],
    "status": "OK"
}

MOCK_GOOGLE_RESPONSE_ZERO_RESULTS = {
    "results": [],
    "status": "ZERO_RESULTS"
}


class TestPharmacySearchValidation:
    """Test input validation for pharmacy search endpoint"""

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_valid_request(self):
        """Test that valid coordinates and radius are accepted"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_SUCCESS
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "OK"
            assert data["count"] == 2
            assert len(data["pharmacies"]) == 2

    def test_invalid_latitude_too_high(self):
        """Test that latitude > 90 is rejected"""
        response = client.get(
            "/pharmacies",
            params={"latitude": 91.0, "longitude": -71.1211, "radius": 5000}
        )
        assert response.status_code == 400
        assert "Invalid latitude" in response.json()["detail"]

    def test_invalid_latitude_too_low(self):
        """Test that latitude < -90 is rejected"""
        response = client.get(
            "/pharmacies",
            params={"latitude": -91.0, "longitude": -71.1211, "radius": 5000}
        )
        assert response.status_code == 400
        assert "Invalid latitude" in response.json()["detail"]

    def test_invalid_longitude_too_high(self):
        """Test that longitude > 180 is rejected"""
        response = client.get(
            "/pharmacies",
            params={"latitude": 42.3318, "longitude": 181.0, "radius": 5000}
        )
        assert response.status_code == 400
        assert "Invalid longitude" in response.json()["detail"]

    def test_invalid_longitude_too_low(self):
        """Test that longitude < -180 is rejected"""
        response = client.get(
            "/pharmacies",
            params={"latitude": 42.3318, "longitude": -181.0, "radius": 5000}
        )
        assert response.status_code == 400
        assert "Invalid longitude" in response.json()["detail"]

    def test_invalid_radius_too_small(self):
        """Test that radius < 500 is rejected"""
        response = client.get(
            "/pharmacies",
            params={"latitude": 42.3318, "longitude": -71.1211, "radius": 499}
        )
        assert response.status_code == 400
        assert "Radius must be between 500m and 50km" in response.json()["detail"]

    def test_invalid_radius_too_large(self):
        """Test that radius > 50000 is rejected"""
        response = client.get(
            "/pharmacies",
            params={"latitude": 42.3318, "longitude": -71.1211, "radius": 50001}
        )
        assert response.status_code == 400
        assert "Radius must be between 500m and 50km" in response.json()["detail"]

    def test_missing_latitude(self):
        """Test that missing latitude parameter is rejected"""
        response = client.get(
            "/pharmacies",
            params={"longitude": -71.1211, "radius": 5000}
        )
        assert response.status_code == 422  # FastAPI validation error

    def test_missing_longitude(self):
        """Test that missing longitude parameter is rejected"""
        response = client.get(
            "/pharmacies",
            params={"latitude": 42.3318, "radius": 5000}
        )
        assert response.status_code == 422  # FastAPI validation error

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_default_radius(self):
        """Test that radius defaults to 5000 when not provided"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_SUCCESS
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211}
            )
            
            assert response.status_code == 200
            # Verify that the default radius was used in the Google API call
            call_params = mock_get.call_args[1]['params']
            assert call_params['radius'] == 5000

    def test_boundary_latitude_90(self):
        """Test that latitude = 90 is accepted"""
        with patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'}):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_ZERO_RESULTS
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                response = client.get(
                    "/pharmacies",
                    params={"latitude": 90.0, "longitude": 0.0, "radius": 5000}
                )
                assert response.status_code == 200

    def test_boundary_latitude_negative_90(self):
        """Test that latitude = -90 is accepted"""
        with patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'}):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_ZERO_RESULTS
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                response = client.get(
                    "/pharmacies",
                    params={"latitude": -90.0, "longitude": 0.0, "radius": 5000}
                )
                assert response.status_code == 200

    def test_boundary_longitude_180(self):
        """Test that longitude = 180 is accepted"""
        with patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'}):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_ZERO_RESULTS
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                response = client.get(
                    "/pharmacies",
                    params={"latitude": 0.0, "longitude": 180.0, "radius": 5000}
                )
                assert response.status_code == 200

    def test_boundary_longitude_negative_180(self):
        """Test that longitude = -180 is accepted"""
        with patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'}):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_ZERO_RESULTS
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                response = client.get(
                    "/pharmacies",
                    params={"latitude": 0.0, "longitude": -180.0, "radius": 5000}
                )
                assert response.status_code == 200

    def test_boundary_radius_500(self):
        """Test that radius = 500 is accepted"""
        with patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'}):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_ZERO_RESULTS
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                response = client.get(
                    "/pharmacies",
                    params={"latitude": 42.3318, "longitude": -71.1211, "radius": 500}
                )
                assert response.status_code == 200

    def test_boundary_radius_50000(self):
        """Test that radius = 50000 is accepted"""
        with patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'}):
            with patch('requests.get') as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_ZERO_RESULTS
                mock_response.raise_for_status = Mock()
                mock_get.return_value = mock_response

                response = client.get(
                    "/pharmacies",
                    params={"latitude": 42.3318, "longitude": -71.1211, "radius": 50000}
                )
                assert response.status_code == 200

class TestPharmacySearchGoogleAPI:
    """Test Google Places API integration"""

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_successful_api_call(self):
        """Test successful Google Places API call"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_SUCCESS
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "pharmacies" in data
            assert "count" in data
            assert "status" in data
            
            # Verify pharmacy data
            assert len(data["pharmacies"]) == 2
            assert data["count"] == 2
            assert data["status"] == "OK"
            
            # Verify first pharmacy
            pharmacy1 = data["pharmacies"][0]
            assert pharmacy1["name"] == "CVS Pharmacy"
            assert pharmacy1["address"] == "123 Main St, Brookline"
            assert pharmacy1["latitude"] == 42.3318
            assert pharmacy1["longitude"] == -71.1211
            assert pharmacy1["rating"] == 4.2
            assert pharmacy1["open_now"] is True
            
            # Verify second pharmacy
            pharmacy2 = data["pharmacies"][1]
            assert pharmacy2["name"] == "Walgreens"
            assert pharmacy2["open_now"] is False

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_zero_results(self):
        """Test handling of zero results from Google API"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_ZERO_RESULTS
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["pharmacies"] == []
            assert data["count"] == 0
            assert data["status"] == "ZERO_RESULTS"

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_api_request_failure(self):
        """Test handling of Google API request failure"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            assert response.status_code == 502
            assert "Failed to fetch pharmacies" in response.json()["detail"]

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_api_timeout(self):
        """Test handling of API timeout"""
        with patch('requests.get') as mock_get:
            import requests
            mock_get.side_effect = requests.Timeout("Request timed out")

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            assert response.status_code == 502
            assert "Failed to fetch pharmacies" in response.json()["detail"]


    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_pharmacy_without_rating(self):
        """Test handling of pharmacy without rating"""
        mock_response_no_rating = {
            "results": [
                {
                    "place_id": "ChIJ789",
                    "name": "Local Pharmacy",
                    "vicinity": "789 Street",
                    "geometry": {
                        "location": {
                            "lat": 42.0,
                            "lng": -71.0
                        }
                    }
                    # No rating, opening_hours, or icon
                }
            ],
            "status": "OK"
        }
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_no_rating
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            assert response.status_code == 200
            data = response.json()
            pharmacy = data["pharmacies"][0]
            
            # Verify optional fields can be None
            assert pharmacy["rating"] is None
            assert pharmacy["open_now"] is None
            assert pharmacy["icon"] is None


class TestPharmacySearchResponseFormat:
    """Test response format and structure"""

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_response_structure(self):
        """Test that response has correct structure"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_SUCCESS
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            data = response.json()
            
            # Check top-level keys
            assert set(data.keys()) == {"pharmacies", "count", "status"}
            
            # Check pharmacies is a list
            assert isinstance(data["pharmacies"], list)
            
            # Check count is an integer
            assert isinstance(data["count"], int)
            
            # Check status is a string
            assert isinstance(data["status"], str)

    @patch.dict('os.environ', {'GOOGLE_PLACES_API_KEY': 'test_key_123'})
    def test_pharmacy_object_structure(self):
        """Test that each pharmacy object has correct structure"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = MOCK_GOOGLE_RESPONSE_SUCCESS
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            response = client.get(
                "/pharmacies",
                params={"latitude": 42.3318, "longitude": -71.1211, "radius": 5000}
            )
            
            data = response.json()
            pharmacy = data["pharmacies"][0]
            
            # Check all expected keys are present
            expected_keys = {
                "place_id", "name", "address", "latitude", 
                "longitude", "rating", "open_now", "icon"
            }
            assert set(pharmacy.keys()) == expected_keys
            
            # Check data types
            assert isinstance(pharmacy["place_id"], str)
            assert isinstance(pharmacy["name"], str)
            assert isinstance(pharmacy["address"], str)
            assert isinstance(pharmacy["latitude"], float)
            assert isinstance(pharmacy["longitude"], float)
            # rating, open_now, icon can be None
            if pharmacy["rating"] is not None:
                assert isinstance(pharmacy["rating"], (int, float))
            if pharmacy["open_now"] is not None:
                assert isinstance(pharmacy["open_now"], bool)
            if pharmacy["icon"] is not None:
                assert isinstance(pharmacy["icon"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])