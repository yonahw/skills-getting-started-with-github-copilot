"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name in activities:
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint"""
    
    def test_get_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Drama Club" in data
        
        # Check structure of an activity
        soccer = data["Soccer Team"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert isinstance(soccer["participants"], list)


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer%20Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_duplicate(self, client):
        """Test that signing up twice for the same activity fails"""
        email = "alex@mergington.edu"
        
        # First signup should fail (already registered)
        response = client.post(
            f"/activities/Soccer%20Team/signup?email={email}"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for a non-existent activity"""
        response = client.post(
            "/activities/NonExistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_different_activities(self, client):
        """Test signing up for multiple different activities"""
        email = "multisport@mergington.edu"
        
        # Sign up for Soccer Team
        response1 = client.post(
            f"/activities/Soccer%20Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Sign up for Basketball Club
        response2 = client.post(
            f"/activities/Basketball%20Club/signup?email={email}"
        )
        assert response2.status_code == 200
        
        # Verify both signups
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Soccer Team"]["participants"]
        assert email in activities_data["Basketball Club"]["participants"]


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregister from an activity"""
        email = "alex@mergington.edu"
        
        # Verify participant exists first
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Soccer Team"]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/Soccer%20Team/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_not_signed_up(self, client):
        """Test unregistering a participant who is not signed up"""
        response = client.delete(
            "/activities/Soccer%20Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "not signed up" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from a non-existent activity"""
        response = client.delete(
            "/activities/NonExistent%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_then_unregister(self, client):
        """Test the full cycle of signing up and then unregistering"""
        email = "cycle@mergington.edu"
        activity = "Drama Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]


class TestDataIntegrity:
    """Tests for data integrity and edge cases"""
    
    def test_participants_are_independent(self, client):
        """Test that participant lists are independent across activities"""
        email = "independent@mergington.edu"
        
        # Sign up for Soccer Team
        client.post(f"/activities/Soccer%20Team/signup?email={email}")
        
        # Check that the email is only in Soccer Team
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        assert email in activities_data["Soccer Team"]["participants"]
        assert email not in activities_data["Basketball Club"]["participants"]
        assert email not in activities_data["Drama Club"]["participants"]
    
    def test_activity_count_after_operations(self, client):
        """Test that activity count remains consistent"""
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json())
        
        # Perform some operations
        client.post("/activities/Soccer%20Team/signup?email=counter@mergington.edu")
        client.delete("/activities/Soccer%20Team/unregister?email=alex@mergington.edu")
        
        # Check count is the same
        final_response = client.get("/activities")
        final_count = len(final_response.json())
        
        assert initial_count == final_count
