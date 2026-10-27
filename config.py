import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "jeevanpath-dev-secure-key-change-in-prod")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "jeevanpath.db"))
    # Coordinator access PIN for demo purposes (can be set via env var)
    COORDINATOR_PIN = os.environ.get("COORDINATOR_PIN", "1234")
    TESTING = False

class TestConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    DATABASE_PATH = ":memory:"
    SECRET_KEY = "test-secret-key"
