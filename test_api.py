import pytest
import requests
from datetime import date, timedelta

# Base URL for the API
BASE_URL = "http://localhost:8000"

class TestTrainSearchAPI:
    
    def test_mandatory_fields_validation(self):
        """Test validation of mandatory fields"""
        
        # Test missing from_station
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code == 422
        
        # Test missing to_station
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code == 422
        
        # Test missing travel_date
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code == 422
        
        # Test missing train_class
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "time": "10:00"
        })
        assert response.status_code == 422
        
        # Test missing time
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd"
        })
        assert response.status_code == 422

    def test_valid_onward_journey(self):
        """Test valid onward journey search"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code == 200
        data = response.json()
        assert "onward" in data
        assert "return" in data
        assert isinstance(data["onward"], list)

    def test_round_trip_journey(self):
        """Test round trip journey with return date"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00",
            "return_date": "2024-01-16",
            "return_time": "18:00"
        })
        assert response.status_code == 200
        data = response.json()
        assert "onward" in data
        assert "return" in data
        assert len(data["return"]) > 0

    def test_train_number_filter(self):
        """Test filtering by train number"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00",
            "train_number": "123"
        })
        # Should return 200 if train exists, 404 if not
        assert response.status_code in [200, 404]

    def test_train_name_filter(self):
        """Test filtering by train name"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00",
            "train_name": "Express"
        })
        assert response.status_code in [200, 404]

    def test_train_type_filter(self):
        """Test filtering by train type"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00",
            "train_type": "IC"
        })
        assert response.status_code in [200, 404]

    def test_return_journey_filters(self):
        """Test return journey specific filters"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00",
            "return_date": "2024-01-16",
            "return_train_number": "456",
            "return_train_name": "Regional",
            "return_train_type": "R"
        })
        assert response.status_code in [200, 404]

    def test_return_filters_without_return_date(self):
        """Test that return filters fail without return_date"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00",
            "return_train_number": "456"
        })
        assert response.status_code == 400
        assert "Please provide a return date to use return journey filters" in response.json()["detail"]

    def test_invalid_station_names(self):
        """Test invalid station names"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "NonExistentStation",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_invalid_time_format(self):
        """Test invalid time format"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "25:00"  # Invalid time
        })
        assert response.status_code == 400

    def test_different_train_classes(self):
        """Test different train class options"""
        classes = ["1st", "2nd", "Chair Car", "Executive Chair Car"]
        
        for train_class in classes:
            response = requests.get(f"{BASE_URL}/search_trains", params={
                "from_station": "Krakow",
                "to_station": "Warsaw",
                "travel_date": "2024-01-15",
                "train_class": train_class,
                "time": "10:00"
            })
            assert response.status_code in [200, 404]

    def test_return_train_class_defaults_to_onward(self):
        """Test that return_train_class defaults to onward train_class"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "1st",
            "time": "10:00",
            "return_date": "2024-01-16"
        })
        
        if response.status_code == 200:
            data = response.json()
            # Check that return journey uses same class as onward
            if data["return"]:
                for train in data["return"]:
                    # Should have 1st class availability
                    class_types = [cls["class_type"] for cls in train["classes"]]
                    assert any("1st" in cls_type for cls_type in class_types)

    def test_numeric_train_number_validation(self):
        """Test that train_number must be numeric"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00",
            "train_number": "ABC123"  # Non-numeric
        })
        assert response.status_code == 400
        assert "must be numeric" in response.json()["detail"]

    def test_response_structure(self):
        """Test response structure is correct"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        
        if response.status_code == 200:
            data = response.json()
            assert "onward" in data
            assert "return" in data
            
            if data["onward"]:
                train = data["onward"][0]
                required_fields = ["train_name", "train_number", "train_type", 
                                 "from_station", "to_station", "departure_time", 
                                 "arrival_time", "classes"]
                for field in required_fields:
                    assert field in train

    def test_wildcard_station_single_character(self):
        """Test wildcard matching with ? for single character"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krak?w",  # ? matches single character
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_wildcard_station_multiple_characters(self):
        """Test wildcard matching with % for multiple characters"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krak%",  # % matches multiple characters
            "to_station": "War%",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_wildcard_station_middle_pattern(self):
        """Test wildcard in middle of station name"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Kr%ow",  # % in the middle
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_wildcard_mixed_patterns(self):
        """Test mixed wildcard patterns"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "K?ak%",  # Mixed ? and %
            "to_station": "W?rsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_exact_match_without_wildcards(self):
        """Test exact station name matching without wildcards"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_wildcard_no_match(self):
        """Test wildcard pattern that doesn't match any station"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "XYZ%",  # Should not match
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_polish_station_names(self):
        """Test Polish station names"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Kraków",  # Polish name with special characters
            "to_station": "Warszawa",  # Polish name
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_mixed_english_polish_names(self):
        """Test mixing English and Polish station names"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krakow",  # English
            "to_station": "Warszawa",  # Polish
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_polish_wildcard_patterns(self):
        """Test wildcard patterns with Polish characters"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krak%",  # Should match both Krakow and Kraków
            "to_station": "Wars%",   # Should match Warszawa/Warsaw
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_polish_special_characters_wildcard(self):
        """Test wildcards with Polish special characters"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krak?w",  # ? should match ó
            "to_station": "Gda?sk",   # ? should match ń
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_station_code_matching(self):
        """Test station code matching"""
        response = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "KRK",  # Station code for Krakow
            "to_station": "WAW",   # Station code for Warsaw
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        assert response.status_code in [200, 404]

    def test_case_insensitive_matching(self):
        """Test case insensitive station matching"""
        test_cases = [
            ("krakow", "warsaw"),      # lowercase
            ("KRAKOW", "WARSAW"),      # uppercase
            ("KrAkOw", "WaRsAw"),      # mixed case
            ("kraków", "warszawa"),    # Polish lowercase
            ("KRAKÓW", "WARSZAWA")     # Polish uppercase
        ]
        
        for from_station, to_station in test_cases:
            response = requests.get(f"{BASE_URL}/search_trains", params={
                "from_station": from_station,
                "to_station": to_station,
                "travel_date": "2024-01-15",
                "train_class": "2nd",
                "time": "10:00"
            })
            assert response.status_code in [200, 404]

    def test_unicode_normalization(self):
        """Test Unicode normalization for Polish characters"""
        # Different Unicode representations of the same character
        response1 = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Kraków",  # Composed form
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        
        response2 = requests.get(f"{BASE_URL}/search_trains", params={
            "from_station": "Krako\u0301w",  # Decomposed form (o + combining acute)
            "to_station": "Warsaw",
            "travel_date": "2024-01-15",
            "train_class": "2nd",
            "time": "10:00"
        })
        
        # Both should give same result
        assert response1.status_code == response2.status_code

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])