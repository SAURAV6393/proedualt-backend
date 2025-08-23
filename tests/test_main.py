import sys
import os
from fastapi.testclient import TestClient

# Add the parent directory to the Python path
# This allows the test to find the 'main' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app # Import your FastAPI app

client = TestClient(app)

def test_get_jobs_endpoint():
    response = client.get("/jobs")
    # Check if the request was successful (status code 200)
    assert response.status_code == 200
    # Check if the response is a list (JSON array)
    assert isinstance(response.json(), list)