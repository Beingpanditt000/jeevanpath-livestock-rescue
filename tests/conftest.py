import os
import tempfile
import pytest
from app import create_app
from database import init_db
from seed_data import seed_database
from config import Config

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"

@pytest.fixture
def app_instance():
    """Create a temporary database and configured test application instance."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    class CustomTestConfig(TestConfig):
        DATABASE_PATH = db_path

    app = create_app(CustomTestConfig)
    init_db(db_path)
    seed_database(db_path)

    yield app

    # Cleanup temp database
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass

@pytest.fixture
def client(app_instance):
    """A test client for the app."""
    return app_instance.test_client()

@pytest.fixture
def coordinator_client(app_instance):
    """A test client pre-authenticated as a Coordinator."""
    cl = app_instance.test_client()
    cl.post("/login", data={
        "username": "coord_admin",
        "password": "CoordPass123!"
    })
    return cl

@pytest.fixture
def farmer_client(app_instance):
    """A test client pre-authenticated as a Farmer."""
    cl = app_instance.test_client()
    cl.post("/login", data={
        "username": "farmer_ramesh",
        "password": "FarmerPass123!"
    })
    return cl

@pytest.fixture
def volunteer_client(app_instance):
    """A test client pre-authenticated as a Volunteer."""
    cl = app_instance.test_client()
    cl.post("/login", data={
        "username": "volunteer_bhaben",
        "password": "VolunteerPass123!"
    })
    return cl

@pytest.fixture
def runner(app_instance):
    """A test CLI runner."""
    return app_instance.test_cli_runner()
